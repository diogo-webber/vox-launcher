
from customtkinter import CTkFrame, CTkLabel, CTkEntry
from tkinter import filedialog, StringVar, DISABLED, NORMAL
from pathlib import Path
import logging

from strings import STRINGS
from constants import COLOR, OFFSET, SIZE, LOGGER, Pos
from widgets.buttons import ImageButton
from helpers import get_key_from_ini_file, get_shard_names
from fonts import Fonts

logger = logging.getLogger(LOGGER)

class CustomEntry(CTkEntry):
    def __init__(self, master, tooltip, pos, size, **kwargs):
        FONT = Fonts()

        self.entrytext = StringVar()
        self._master = master
        self.valid = None

        self.fixer_frame = CTkFrame(
            master=self._master,
            border_color=COLOR.GRAY,
            fg_color=COLOR.GRAY,
            border_width=0,
            corner_radius=10,
            width=size.w,
            height=size.h,
        )

        self.fixer_frame.place(
            x=pos.x,
            y=pos.y,
        )

        super().__init__(
            master = self.fixer_frame,
            corner_radius=10,
            border_color=COLOR.GRAY,
            text_color=COLOR.WHITE,
            fg_color=COLOR.GRAY,
            font=FONT.ENTRY,
            border_width=0,
            height=size.h,
            width=size.w - size.h - 8,
            textvariable=self.entrytext,
            **kwargs)

        self._entry.configure(selectbackground=COLOR.DARK_GRAY)

        self.place(
            x=5,
            y=-1,
        )

        self.tooltip = CTkLabel(
            master=self._master,
            height=0,
            anchor="nw",
            text=tooltip,
            text_color=COLOR.WHITE,
            fg_color="transparent",
            font=FONT.ENTRY_TOOLTIP,
        )

        self.tooltip.place(
            x= pos.x + OFFSET.ENTRY_TOOLTIP.x,
            y= pos.y + OFFSET.ENTRY_TOOLTIP.y,
        )

        self.tooltip.update()

        self.invalid_text = CTkLabel(
            master=self._master,
            height=0,
            anchor="nw",
            text=STRINGS.ENTRY.ENTRY_INVALID_INPUT,
            text_color=COLOR.RED,
            text_color_disabled=COLOR.DARK_GRAY,
            fg_color="transparent",
            font=FONT.INVALID_INPUT,
        )

        self.invalid_text.place(
            x = pos.x + self.tooltip.winfo_width() + OFFSET.INVALID_INPUT.x,
            y = pos.y + OFFSET.INVALID_INPUT.y,
        )

        self.toggle_warning(True)

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
        self.xview_moveto(1.0)

        if not load:
            self._master.save_entries_data()

    def disable(self):
        self._entry.configure(state=DISABLED)

    def enable(self):
        self._entry.configure(state=NORMAL)

class DirectoryEntry(CustomEntry):
    def __init__(self, initialdir, validate_fn, pos, size, **kwargs):
        self.initialdir = initialdir
        self.validate_fn = validate_fn

        super().__init__(
            pos=pos,
            size=size,
            **kwargs
        )

        button_image_size = self._apply_widget_scaling(SIZE.DIRECTORY_ENTRY.h - 23.5)

        self.button = ImageButton(
            master=self.fixer_frame,
            image="assets/directory.png",
            command=self.open_directory_dialog,
            width=size.h,
            height=size.h,
            hover=False,
            image_size=(button_image_size, button_image_size),
            pos=Pos(size.w - size.h - 10, -1)
        )

        self.button.show()

        self.bind("<FocusOut>", self.on_text_changed)

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
            token = token_file.read_text(encoding="utf-8")

            self._master.token_entry.set_text(token)

        if config_file.exists():
            cluster_name = get_key_from_ini_file(config_file, "cluster_name")

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

        button_image_size = self._apply_widget_scaling(SIZE.DIRECTORY_ENTRY.h - 23.5)

        self.button = ImageButton(
            master=self.fixer_frame,
            image="assets/eye.png",
            command=self.toggle_text_visibility,
            width=size.h,
            height=size.h,
            hover=False,
            image_size=(button_image_size, button_image_size),
            pos=Pos(size.w - size.h - 10, 0)
        )

        self.button.show()

    def toggle_text_visibility(self):
        self.configure(show=self.showing and "●" or "")

        self.showing = not self.showing