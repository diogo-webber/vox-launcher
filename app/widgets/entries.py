
from customtkinter import CTkFrame, CTkLabel, CTkEntry
from tkinter import filedialog, StringVar, DISABLED, NORMAL
from pathlib import Path
import logging

from strings import STRINGS
from constants import COLOR, OFFSET, SIZE, LOGGER, Pos, Size
from widgets.buttons import ImageButton
from widgets.frames import CustomFrame
from helpers import get_sanitized_cluster_name, get_shard_names, redraw_safe_size
from fonts import FONT

logger = logging.getLogger(LOGGER)

class CustomEntry(CTkFrame):
    """ Rounded container holding an entry, leaving room on the right for a subclass' icon button. """

    def __init__(self, master, tooltip, pos, size, **kwargs):
        self.entrytext = StringVar()
        self._master = master
        self.valid = None

        super().__init__(
            master=master,
            border_color=COLOR.GRAY,
            fg_color=COLOR.GRAY,
            border_width=0,
            corner_radius=10,
            width=size.w,
            height=size.h,
        )

        self.box = Size(redraw_safe_size(self, size.w), redraw_safe_size(self, size.h))

        self.configure(width=self.box.w, height=self.box.h)

        self.place(
            x=pos.x,
            y=pos.y,
        )

        self.entry = CTkEntry(
            master=self,
            corner_radius=10,
            border_color=COLOR.GRAY,
            text_color=COLOR.WHITE_HOVER,
            fg_color=COLOR.GRAY,
            font=FONT.ENTRY_ARIAL,
            border_width=0,
            # 1px shorter: CTk draws a frame's rounded shape 2px short of its box, and the
            # entry's leftover canvas is flat-filled, which would jut out below the curve.
            height=self.box.h - 1,
            width=self.box.w - self.box.h - 8,
            textvariable=self.entrytext,
            **kwargs
        )

        self.entry._entry.configure(selectbackground=COLOR.DARK_GRAY)

        self.entry.place(
            x=8,
            y=0,
        )

        self._tooltip_frame = CustomFrame(
            master=self._master,
            color=COLOR.DARK_GRAY,
            size=Size(0, 0),
            pos=Pos(pos.x + OFFSET.ENTRY_TOOLTIP.x, pos.y + OFFSET.ENTRY_TOOLTIP.y),
        )

        self.tooltip = CTkLabel(
            master=self._tooltip_frame,
            height=0,
            anchor="center",
            text=tooltip,
            text_color=COLOR.WHITE,
            fg_color="transparent",
            font=FONT.ENTRY_TOOLTIP,
        )

        self.invalid_text = CTkLabel(
            master=self._tooltip_frame,
            height=0,
            anchor="center",
            text=STRINGS.ENTRY.ENTRY_INVALID_INPUT,
            text_color=COLOR.RED,
            text_color_disabled=COLOR.DARK_GRAY,
            fg_color="transparent",
            font=FONT.INVALID_INPUT,
        )

        self.tooltip.grid(
            row = 0,
            column = 0,
            padx=(0, OFFSET.INVALID_INPUT.x),
            sticky="s",
        )

        self.invalid_text.grid(
            row = 0,
            column = 1,
            sticky="s",
        )

        self.toggle_warning(True)

    def _add_icon_button(self, image, command):
        image_size = self.box.h / 2

        button = ImageButton(
            master=self,
            image=image,
            command=command,
            width=0,
            height=0,
            hover=False,
            image_size=(image_size, image_size),
            pos=Pos(self.box.w - image_size * 2, self.box.h / 5)
        )

        button.show()

        return button

    def get(self):
        return self.entry.get()

    def set_text(self, text, load=False):
        if text != "":
            self.entrytext.set(text)

            self.on_text_changed(load=load)

    def toggle_warning(self, valid):
        self.valid = valid

        if not self.valid:
            logger.info(f"Invalid input at entry {self.tooltip.cget('text')}.")

        self.invalid_text.configure(state=self.valid and DISABLED or NORMAL)

    def validate_text(self):
        pass

    def on_text_changed(self, load=False):
        self.validate_text()

        # "Scroll" to the X end.
        self.entry.xview_moveto(1.0)

        if not load:
            self._master.save_entries_data()

    def disable(self):
        self.entry._entry.configure(state=DISABLED, cursor="no")

    def enable(self):
        self.entry._entry.configure(state=NORMAL, cursor="xterm")

class DirectoryEntry(CustomEntry):
    def __init__(self, initialdir, validate_fn, pos, size, **kwargs):
        self.initialdir = initialdir
        self.validate_fn = validate_fn

        super().__init__(
            pos=pos,
            size=size,
            **kwargs
        )

        self.button = self._add_icon_button("assets/directory.png", self.open_directory_dialog)

        self.entry.bind("<FocusOut>", self.on_text_changed)

    def validate_text(self):
        valid = self.validate_fn(self.get())

        self.toggle_warning(valid)

        return valid

    def open_directory_dialog(self):
        directory = filedialog.askdirectory(
            title=STRINGS.ASK_DIRECTORY_TITLE,
            initialdir=self.initialdir
        )

        if not directory:
            return

        self.set_text(directory)

    def disable(self):
        super().disable()
        self.button.disable()

    def enable(self):
        super().enable()
        self.button.enable()

class ClusterDirectoryEntry(DirectoryEntry):
    def on_text_changed(self, *args, load=False):
        super().on_text_changed(load=load)

        directory_path = Path(self.get())

        token_file =  directory_path / "cluster_token.txt"
        config_file =  directory_path / "cluster.ini"

        if token_file.exists():
            token = token_file.read_text(encoding="utf-8", errors="backslashreplace")

            self._master.token_entry.set_text(token)

        if config_file.exists():
            cluster_name = get_sanitized_cluster_name(config_file)

            self._master.cluster_name.text.set(cluster_name or STRINGS.CLUSTER_NAME_DEFAULT)

            if self.valid:
                shard_names = get_shard_names(directory_path)
                single_shard = len(shard_names) == 1

                current_shards = list(self._master.shard_group.shards.keys())

                rebuild = current_shards != shard_names and not (single_shard and "PlaceHolder" in current_shards)

                if rebuild:
                    self._master.shard_group.remove_all_shards()

                    for shard_name in shard_names:
                        self._master.shard_group.add_shard(code=shard_name)

                    if single_shard:
                        self._master.shard_group.add_placeholder_shard()
                else:
                    # I hate this a lot, thinking about rebuilding at least the log panel.
                    for shard in self._master.shard_group.shards.values():
                        shard.cleanup_state()

                return

        self._master.shard_group.remove_all_shards()
        self._master.cluster_name.text.set(STRINGS.CLUSTER_NAME_DEFAULT)


class TokenEntry(CustomEntry):
    def __init__(self, pos, size, **kwargs):
        self.showing = False

        super().__init__(
            pos=pos,
            size=size,
            **kwargs
        )

        self.button = self._add_icon_button("assets/eye.png", self.toggle_text_visibility)

    def toggle_text_visibility(self):
        self.entry.configure(show=self.showing and "●" or "")

        self.showing = not self.showing