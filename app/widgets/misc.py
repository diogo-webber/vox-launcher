from pathlib import Path

from customtkinter import CTkImage, CTkLabel, CTkToplevel, CTkButton, CTkSlider
from tkinter import StringVar, IntVar, Toplevel, filedialog, DISABLED, NORMAL, TclError
from tkinter import font as tkfont
from PIL import Image
import requests, os, zipfile

from strings import STRINGS
from constants import COLOR, SIZE, POS, Size, PATCH_NOTES_URL, CLUSTER_STATS_PADX
from settings_manager import Settings
from widgets.frames import CustomFrame
from helpers import resource_path, open_file, open_github_issue, open_url, add_folder_to_zip, can_update_in_place, stage_update
from fonts import FONT

class ClusterStats:
    # Only these keys are accepted from the server output.
    STAT_KEYS = ("day", "season", "players")

    def __init__(self, master) -> None:
        # Label whose text baseline the stats line up with, once shown.
        self.baseline_reference = None

        self.day     = StringVar()
        self.season  = StringVar()
        self.players = StringVar()

        self._frame = CustomFrame(
            master=master,
            color=COLOR.DARK_GRAY,
            size=SIZE.CLUSTER_STATS,
            pos=POS.CLUSTER_STATS,
        )

        # CTkFrame shrinks to its children, which would pull the labels above the dropdown's centre.
        self._frame.grid_propagate(False)
        self._frame.grid_rowconfigure(0, weight=1)

        self.day_label     = self.create_stats_label(self.day,     title=STRINGS.CLUSTER_STATS.DAY,     column=0)
        self.season_label  = self.create_stats_label(self.season,  title=STRINGS.CLUSTER_STATS.SEASON,  column=2)
        self.players_label = self.create_stats_label(self.players, title=STRINGS.CLUSTER_STATS.PLAYERS, column=4)

        self.hide()

    def create_stats_label(self, textvariable, title, column):
        title_label =  CTkLabel(
            master=self._frame,
            height=0,
            anchor="nw",
            text=title,
            text_color=COLOR.WHITE_HOVER,
            font=FONT.CLUSTER_STATS,
        )

        value_label =  CTkLabel(
            master=self._frame,
            height=0,
            anchor="nw",
            textvariable=textvariable,
            text_color=COLOR.WHITE,
            font=FONT.CLUSTER_STATS,
        )

        title_label.grid(
            row = 0,
            column = column,
            padx=(CLUSTER_STATS_PADX, 5),
        )

        value_label.grid(
            row = 0,
            column = column + 1,
        )

        return title_label

    def update(self, data: dict):
        self.show()

        for k, v in data.items():
            if k in self.STAT_KEYS:
                getattr(self, k).set(str(v))

    def show(self):
        shown = bool(self._frame.winfo_manager())

        self._frame.place(
            x=POS.CLUSTER_STATS.x,
            y=POS.CLUSTER_STATS.y,
        )

        if not shown and self.baseline_reference is not None:
            self._align_baseline()

    @staticmethod
    def _baseline(label):
        """ Screen y of the text's baseline, from the font actually drawn (CTk scales it). """

        inner = label._label
        font = tkfont.Font(font=inner.cget("font"))

        return inner.winfo_rooty() + (inner.winfo_height() - font.metrics("linespace")) / 2 + font.metrics("ascent")

    def _align_baseline(self):
        """ Moves the stats so their text sits on the baseline of the reference label, whose font is bigger. """

        self._frame.update_idletasks()

        gap = self._baseline(self.baseline_reference) - self._baseline(self.day_label)

        self._frame.place(
            x=POS.CLUSTER_STATS.x,
            y=POS.CLUSTER_STATS.y + gap / self._frame._get_widget_scaling(),
        )

    def hide(self):
        self._frame.place_forget()

TOOLTIP_PADDING = 7
TOOLTIP_GAP = 8
TOOLTIP_LINE_GAP = 5
TOOLTIP_WINDOW_MARGIN = 14
TOOLTIP_TRANSPARENT_COLOR = "#010203"  # Keyed out by the window manager, so it must not appear in the tooltip.

class Tooltip:
    def __init__(self, master=None, text="", image=None, pos=None, image_size=None, onclick=None, widget=None, above=False, anchor=None):
        self.text = text
        self.pos = pos
        self.image_size = image_size
        self.tooltip = None
        self.taskid = None
        self.above = above
        self.cursor = onclick and "hand2" or None

        if widget is not None:
            # Attached to an existing widget rather than owning an icon of its own.
            self.widget = widget
        else:
            image = CTkImage(Image.open(resource_path(image)), size=self.image_size)

            self.widget = CTkLabel(
                master=master,
                image=image,
                text='',
            )

            self.widget.place(
                x=pos.x,
                y=pos.y,
            )

        self.widget.bind("<Enter>", self.show_tooltip_with_delay)
        self.widget.bind("<Leave>", self.hide_tooltip)

        # What the tooltip is placed against, when that isn't the widget it pops up from.
        self.anchor = anchor or self.widget

        if onclick:
            self.widget.bind("<Button-1>", onclick)

    def add_trigger(self, widget, can_show=None):
        """ Extra widget that also opens this tooltip on hover, gated by can_show. """

        def on_enter(event=None):
            if can_show is None or can_show():
                self.show_tooltip_with_delay(event)

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", self.hide_tooltip)

    def set_text(self, text):
        self.text = text

        if not text:
            self.hide_tooltip()

    def _is_disabled(self):
        try:
            return str(self.widget.cget("state")) == DISABLED

        except (TclError, ValueError):
            return False # Widget has no state, so it can't be disabled.

    def show_tooltip_with_delay(self, event=None):
        if not self.text or self._is_disabled():
            return

        if self.taskid:
            self.widget.after_cancel(self.taskid)

        self.taskid = self.widget.after(250, self.show_tooltip)

    def show_tooltip(self):
        if self.cursor:
            self.widget.configure(cursor=self.cursor)

        self.tooltip = Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.configure(bg=TOOLTIP_TRANSPARENT_COLOR)
        self.tooltip.wm_attributes("-transparentcolor", TOOLTIP_TRANSPARENT_COLOR)

        self.tooltip_frame = CustomFrame(
            master=self.tooltip,
            color=COLOR.GRAY,
            size=Size(0, 0),
            corner_radius=8,
            bg_color=TOOLTIP_TRANSPARENT_COLOR,
            border_color=COLOR.GRAY_HOVER,
            border_width=2,
        )

        padding = self.tooltip_frame._apply_widget_scaling(TOOLTIP_PADDING)
        line_gap = self.tooltip_frame._apply_widget_scaling(TOOLTIP_LINE_GAP)

        # One label per line, so the gap between them can be controlled.
        lines = self.text.split("\n")

        for index, line in enumerate(lines):
            label = CTkLabel(
                self.tooltip_frame,
                width=0,
                height=0,
                text=line,
                fg_color="transparent",
                text_color=COLOR.WHITE,
                font=FONT.TOOLTIP_SMALL,
                wraplength=330,
            )

            label.pack(
                padx = padding,
                pady = (
                    index == 0 and padding or line_gap,
                    index == len(lines) - 1 and padding or 0,
                ),
            )

        self.tooltip_frame.pack()

        try:
            self.tooltip_frame.update()

            tooltip_width  = self.tooltip_frame.winfo_reqwidth()
            tooltip_height = self.tooltip_frame.winfo_reqheight()

            gap = self.tooltip_frame._apply_widget_scaling(TOOLTIP_GAP)
            margin = self.tooltip_frame._apply_widget_scaling(TOOLTIP_WINDOW_MARGIN)

            window = self.widget.winfo_toplevel()

            window_left   = window.winfo_rootx()    + margin
            window_top    = window.winfo_rooty()    + margin
            window_right  = window_left + window.winfo_width()  - margin * 2
            window_bottom = window_top  + window.winfo_height() - margin * 2

            above_y = self.anchor.winfo_rooty() - tooltip_height - gap
            below_y = self.anchor.winfo_rooty() + self.anchor.winfo_height() + gap

            # Centered on the anchor, flipped to the other side when there's no room.
            x = self.anchor.winfo_rootx() + self.anchor.winfo_width()/2 - tooltip_width/2
            y = self.above and above_y or below_y

            if self.above and y < window_top:
                y = below_y

            elif not self.above and y + tooltip_height > window_bottom:
                y = above_y

            # Never overflow the app window.
            x = max(window_left, min(x, window_right  - tooltip_width))
            y = max(window_top,  min(y, window_bottom - tooltip_height))

            self.tooltip.wm_geometry(f"+{round(x)}+{round(y)}")
        except Exception:
            # Tooltip was destroyed during update() by a pending <Leave> event.
            self.tooltip = None

    def hide_tooltip(self, event=None):
        if self.cursor:
            self.widget.configure(cursor="arrow")

        if self.taskid:
            self.widget.after_cancel(self.taskid)

            self.taskid = None

        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

class PopUp:
    def __init__(self, root):
        self.root = root
        self.popup = None
        self.confirmed = None
        self.slider_value = None
        self.button_1_text = STRINGS.POPUP.OK
        self.button_2_text = ""

    def create(self, text, slider_fn=None):
        if self.popup is not None:
            # Only one popup.
            return self.confirmed, self.slider_value

        self.confirmed = None
        self.slider_value = None

        self.popup = CTkToplevel(self.root, fg_color=COLOR.GRAY)
        self.popup.wm_overrideredirect(True)
        self.popup.grab_set()  # Make other windows not clickable.

        # Each button spans two columns, so all four must stay equal or they end up different widths.
        self.popup.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="popup")
        self.popup.rowconfigure(0, weight=1)

        self.popup._frame = CustomFrame(
            master=self.popup,
            color=COLOR.GRAY,
            border_color=COLOR.WHITE,
            pos=POS.POPUP,
            size=SIZE.POPUP,
            corner_radius=10,
            border_width=1,
        )

        self.popup._label = CTkLabel(
            master=self.popup,
            width=SIZE.POPUP.w,
            wraplength=SIZE.POPUP.w,
            fg_color="transparent",
            text_color=COLOR.WHITE,
            text=text,
            font=FONT.POPUP,
            justify="left",
        )

        self.popup.button_1 = CTkButton(
            master=self.popup,
            width=50,
            fg_color=COLOR.DARK_GRAY,
            hover_color=COLOR.DARK_GRAY,
            text_color=COLOR.WHITE,
            border_color=COLOR.WHITE,
            border_width=0,

            text=self.button_1_text,
            font=FONT.SMALL_BUTTON,
            command=self.button_1_callback,
        )

        self.popup.button_2 = CTkButton(
            master=self.popup,
            width=50,
            fg_color=COLOR.DARK_GRAY,
            hover_color=COLOR.DARK_GRAY,
            text_color=COLOR.WHITE,
            border_color=COLOR.WHITE,
            border_width=0,
            text=self.button_2_text,
            font=FONT.SMALL_BUTTON,
            command=self.button_2_callback
        )

        has_slider = False

        if slider_fn:
            from_, to = slider_fn(self.root)

            self.slider_value = from_

            # CTkSlider divides by its range, so a single choice gets no slider.
            has_slider = to > from_

        if has_slider:
            self._slider = CTkSlider(
                master=self.popup,
                from_=from_,
                number_of_steps=to - from_,
                to=to,
                command=self._slider_event,
                button_color=COLOR.WHITE,
                button_hover_color=COLOR.WHITE,
                progress_color=COLOR.WHITE,
            )

            self._slider.set(from_)

            self._slider_text = IntVar(value=from_)

            self._slider_label = CTkLabel(
                master=self.popup,
                width=0,
                wraplength=0,
                fg_color="transparent",
                text_color=COLOR.WHITE,
                textvariable=self._slider_text,
                font=FONT.TEXTBOX,
            )

            self._slider_label.grid(row=1, column=0, columnspan=1, padx=(20, 10), pady=(0, 20), sticky="ew")
            self._slider.grid(      row=1, column=1, columnspan=3, padx=(10, 20), pady=(0, 20), sticky="ew")

        buttons_row = has_slider and 2 or 1

        self.popup._label.grid(row=0, column=0, columnspan=4, padx=20, pady=20, sticky="ew")

        self.popup.button_1.grid(row=buttons_row, column=0, columnspan=2, padx=(20, 10), pady=(0, 20), sticky="ew")
        self.popup.button_2.grid(row=buttons_row, column=2, columnspan=2, padx=(10, 20), pady=(0, 20), sticky="ew")

        self.popup.withdraw()
        self.popup.update()

        popup_width = self.popup.winfo_reqwidth()
        popup_height = self.popup.winfo_reqheight()

        self.popup._frame.configure(
            bg_color = COLOR.DARK_GRAY,
            width = popup_width / self.popup._frame._apply_widget_scaling(1.0),
            height = popup_height / self.popup._frame._apply_widget_scaling(1.0),
        )

        master_x = self.root.winfo_rootx()
        master_y = self.root.winfo_rooty()
        master_width = self.root.winfo_width()
        master_height = self.root.winfo_height()

        # Calculate the center position
        x = master_x + (master_width - popup_width) // 2
        y = master_y + (master_height - popup_height) // 2

        # The popup is modal and has no title bar, so an off-screen one would be unrecoverable.
        x = max(0, min(x, self.popup.winfo_screenwidth()  - popup_width))
        y = max(0, min(y, self.popup.winfo_screenheight() - popup_height))

        # Set the window's position.
        self.popup.wm_geometry('+{}+{}'.format(x, y))

        self.popup.bind("<Escape>", lambda event: self.dismiss())

        self.popup.deiconify()
        self.popup.focus_force()  # Without focus the key bindings never fire.

        self.root.wait_window(self.popup)

        return self.confirmed, self.slider_value

    def _close(self):
        if self.popup:
            self.popup.grab_release()
            self.popup.destroy()
            self.popup = None

    def _slider_event(self, value):
        value = round(value)

        self.slider_value = value
        self._slider_text.set(value)

    def button_1_callback(self):
        self._close()

    def button_2_callback(self):
        self._close()

    def dismiss(self):
        """ Bound to Escape. Button 2 is the dismissing one on most popups. """

        self.button_2_callback()

class CommandPopUp(PopUp):
    def __init__(self, root):
        super().__init__(root)
        self.button_2_text = STRINGS.POPUP.CANCEL

    def button_1_callback(self):
        self.confirmed = True

        self._close()

    def button_2_callback(self):
        self.confirmed = False

        self._close()

class ServerErrorPopUp(PopUp):
    def __init__(self, root):
        super().__init__(root)
        self.button_2_text = STRINGS.POPUP.LOG

    def button_1_callback(self):
        self.confirmed = True

        self._close()

    def button_2_callback(self):
        path = Path(self.root.cluster_entry.get()) / "Master/server_log.txt"

        if path.exists():
            open_file(path)

    def dismiss(self):
        self.button_1_callback()

class AppExceptionPopUp(PopUp):
    def __init__(self, root):
        super().__init__(root)

        self.button_2_text = STRINGS.POPUP.REPORT
        self.traceback = None

    def create(self, text, traceback):
        self.traceback = traceback

        return super().create(text)

    def button_1_callback(self):
        self.confirmed = True

        self.root.restart_application()

        self._close()

    def button_2_callback(self):
        open_github_issue(template="app_crash_report", traceback=self.traceback)

    def dismiss(self):
        pass  # Restarting the app is too destructive to trigger with Escape.

class LaunchDataPopUp(PopUp):
    def __init__(self, root):
        super().__init__(root)
        self.button_1_text = STRINGS.POPUP.RETRY
        self.button_2_text = STRINGS.POPUP.CANCEL

    def button_1_callback(self):
        self.root.shard_group.start_all_shards()

        if self.root.master_shard.is_running():
            self._close()

    def button_2_callback(self):
        self.confirmed = False

        self._close()

class RestartRequiredPopUp(PopUp):
    def __init__(self, root):
        super().__init__(root)
        self.button_1_text = STRINGS.POPUP.RESTART
        self.button_2_text = STRINGS.POPUP.CANCEL

    def button_1_callback(self):
        self.confirmed = True

        self._close()

        self.root.restart_application()

    def button_2_callback(self):
        self.confirmed = False

        self._close()

class PatchNotesPopUp(PopUp):
    def __init__(self, root):
        super().__init__(root)
        self.button_2_text = STRINGS.PATCH_NOTES_POPUP.BUTTON

    def button_1_callback(self):
        self.confirmed = True

        self._close()

    def button_2_callback(self):
        open_url(PATCH_NOTES_URL)

        self.confirmed = True

        self._close()

    def dismiss(self):
        self.button_1_callback()

class AppOutdatedPopUp(PopUp):
    def __init__(self, root):
        super().__init__(root)
        self.button_1_text = STRINGS.UPDATE_POPUP.DOWNLOAD
        self.button_2_text = STRINGS.UPDATE_POPUP.IGNORE

    def button_2_callback(self):
        self.confirmed = True

        self._close()

    def set_text(self, text, disabled_buttons=False):
        self.popup._label.configure(text=text)

        self.popup.button_1.configure(state=disabled_buttons and DISABLED or NORMAL)
        self.popup.button_2.configure(state=disabled_buttons and DISABLED or NORMAL)

        self.popup.update()

        popup_width = self.popup.winfo_reqwidth()
        popup_height = self.popup.winfo_reqheight()

        self.popup._frame.configure(
            width = popup_width / self.popup._frame._apply_widget_scaling(1.0),
            height = popup_height / self.popup._frame._apply_widget_scaling(1.0),
        )

        self.popup._frame.update()

    def button_1_callback(self):
        self.set_text(text=STRINGS.UPDATE_POPUP.DESCRIPTION.DOWNLOADING, disabled_buttons=True)

        try:
            response = requests.get(
                url="https://github.com/diogo-webber/vox-launcher/releases/latest/download/VoxLauncher.zip",
                timeout=15,
            )

            response.raise_for_status()  # Raise an exception for HTTP errors.

            if response.status_code == 200 and can_update_in_place():
                self.root.pending_update_script = stage_update(response.content)
                self.root.settings.set(Settings.SHOW_PATCH_NOTES, True)

                self.confirmed = True
                self._close()

                # Closing the app runs the staged update once the process exits.
                self.root.after(0, self.root.on_close)

                return

            if response.status_code == 200:
                file = filedialog.asksaveasfile(
                    mode = "wb",
                    defaultextension = ".zip",
                    initialdir = resource_path("").parent,
                    initialfile = "VoxLauncher.zip",
                    filetypes=[("Zip file", "*.zip")],
                )

                if file:
                    file.write(response.content)
                    file.close()

                    # Set before zipping, so the new version's savedata carries the flag.
                    self.root.settings.set(Settings.SHOW_PATCH_NOTES, True)

                    # Copy save data from current version.
                    savedata = resource_path("savedata")
                    data_dir = Path("appdata")

                    if savedata.exists():
                        add_folder_to_zip(file.name, savedata, data_dir)

                    # Opens the directory in windows explorer.
                    os.startfile(Path(file.name).parent)

                    self.confirmed = True
                    self._close()

                    return

                else:
                    self.set_text(text=STRINGS.UPDATE_POPUP.DESCRIPTION.DEFAULT)
            else:
                self.set_text(text=STRINGS.UPDATE_POPUP.DESCRIPTION.FAILED)

        except (requests.exceptions.RequestException, OSError, zipfile.BadZipFile, FileNotFoundError):
                self.set_text(text=STRINGS.UPDATE_POPUP.DESCRIPTION.FAILED)

        self.confirmed = False