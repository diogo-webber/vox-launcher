from customtkinter import CTkImage, CTkLabel, CTkToplevel, CTkButton, CTkSlider
from tkinter import StringVar, IntVar, Toplevel, END
from PIL import Image

from strings import STRINGS
from constants import COLOR, SIZE, POS, WINDOW_WIDTH, WINDOW_HEIGHT
from widgets.frames import CustomFrame
from helpers import resource_path
from fonts import Fonts

class ClusterStats:
    def __init__(self, master) -> None:
        self.day     = StringVar()
        self.season  = StringVar()
        self.players = StringVar()

        self._frame = CustomFrame(
            master=master,
            color=COLOR.DARK_GRAY,
            size=SIZE.CLUSTER_STATS,
            pos=POS.CLUSTER_STATS,
        )

        self.day_label     = self.create_stats_label(self.day,     title=STRINGS.CLUSTER_STATS.DAY,     column=0)
        self.season_label  = self.create_stats_label(self.season,  title=STRINGS.CLUSTER_STATS.SEASON,  column=2)
        self.players_label = self.create_stats_label(self.players, title=STRINGS.CLUSTER_STATS.PLAYERS, column=4)

        self.hide()

    def create_stats_label(self, textvariable, title, column):
        FONT = Fonts()

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
            padx=(65, 5),
        )

        value_label.grid(
            row = 0,
            column = column + 1,
        )

    def update(self, data: dict):
        self.show()

        for k, v in data.items():
            if hasattr(self, k):
                getattr(self, k).set(str(v))

    def show(self):
        self._frame.place(
            x=POS.CLUSTER_STATS.x,
            y=POS.CLUSTER_STATS.y,
        )

    def hide(self):
        self._frame.place_forget()


class Tooltip:
    def __init__(self, master, text, image, pos, image_size, onclick=None):
        self.text = text
        self.pos = pos
        self.image_size = image_size
        self.tooltip = None
        self.taskid = None

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

        if onclick:
            self.widget.bind("<Button-1>", onclick)

    def show_tooltip_with_delay(self, event=None):
        if self.taskid:
            self.widget.after_cancel(self.taskid)

        self.taskid = self.widget.after(250, self.show_tooltip)

    def show_tooltip(self):
        FONT = Fonts()

        self.widget.configure(cursor="hand2")

        self.tooltip = Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)

        self.tooltip_label = CTkLabel(
            self.tooltip,
            text=self.text,
            fg_color=COLOR.GRAY,
            bg_color=COLOR.DARK_GRAY,
            text_color=COLOR.WHITE,
            corner_radius=10,
            font=FONT.ENTRY,
            wraplength=330,
        )

        self.tooltip_label.pack(ipadx=20, ipady=20)

        self.tooltip_label.update()

        x, y, _, _ = self.widget.bbox()
        x += self.widget.winfo_rootx() - self.tooltip_label.winfo_width() - self.image_size[0]
        y += self.widget.winfo_rooty() - self.tooltip_label.winfo_height() / 4

        self.tooltip.wm_geometry(f"+{round(x)}+{round(y)}")

    def hide_tooltip(self, event=None):
        self.widget.configure(cursor="arrow")

        if self.taskid:
            self.widget.after_cancel(self.taskid)

            self.taskid = None

        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

class PopUp():
    def __init__(self, root):
        self.root = root
        self.confirmed = None
        self.slider_value = None

    def create(self, text, slider_fn=None):
        FONT = Fonts()

        self.popup = CTkToplevel(self.root, fg_color=COLOR.GRAY)
        self.popup.wm_overrideredirect(True)
        self.popup.grab_set()  # Make other windows not clickable.

        self.popup.grid_columnconfigure((0, slider_fn and 4 or 2), weight=1)
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
            font=FONT.POPUP
        )

        self.popup._ok_button = CTkButton(
            master=self.popup,
            width=50,
            fg_color=COLOR.DARK_GRAY,
            hover_color=COLOR.DARK_GRAY,
            text_color=COLOR.WHITE,
            border_color=COLOR.WHITE,
            border_width=0.4,
            text=STRINGS.POPUP.OK,
            font=FONT.SMALL_BUTTON,
            command=self._ok_event,
        )

        self.popup._cancel_button = CTkButton(
            master=self.popup,
            width=50,
            fg_color=COLOR.DARK_GRAY,
            hover_color=COLOR.DARK_GRAY,
            text_color=COLOR.WHITE,
            border_color=COLOR.WHITE,
            border_width=0.4,
            text=STRINGS.POPUP.CANCEL,
            font=FONT.SMALL_BUTTON,
            command=self._cancel_event
        )

        if slider_fn:
            from_, to = slider_fn(self.root)

            self.slider_value = from_

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

            self._slider_text = IntVar(value=1)

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

        buttons_row = slider_fn and 2 or 1

        self.popup._label.grid(        row=0,           column=0, columnspan=4, padx=20,       pady=20,      sticky="ew")
        self.popup._ok_button.grid(    row=buttons_row, column=0, columnspan=2, padx=(20, 10), pady=(0, 20), sticky="ew")
        self.popup._cancel_button.grid(row=buttons_row, column=2, columnspan=2, padx=(10, 20), pady=(0, 20), sticky="ew")

        #self.popup.update()
        #logger.debug(f"POPUP_WIDTH = {self.popup.winfo_width()}")
        #logger.debug(f"POPUP_HEIGHT = {self.popup.winfo_height()}")

        # Static size because .update() function will cause the widget to appear briefly at the wrong place.
        POPUP_WIDTH  = 452
        POPUP_HEIGHT = slider_fn and 246 or 178

        self.popup._frame.configure(
            bg_color = COLOR.DARK_GRAY,
            width = POPUP_WIDTH / 1.5,
            height = POPUP_HEIGHT / 1.5,
        )

        # Magic math :)
        x = self.root.winfo_rootx() + WINDOW_WIDTH  * 0.75 - POPUP_WIDTH  / 2
        y = self.root.winfo_rooty() + WINDOW_HEIGHT * 0.75 - POPUP_HEIGHT / 2

        self.popup.wm_geometry(f"+{round(x)}+{round(y)}")

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

    def _ok_event(self, event=None):
        self.confirmed = True

        self._close()

    def _cancel_event(self):
        self.confirmed = False

        self._close()

