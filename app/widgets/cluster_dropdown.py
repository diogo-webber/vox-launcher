import logging
from datetime import date
from pathlib import Path

import customtkinter as ctk
from PIL import Image

from constants import COLOR, CLUSTER_DROPDOWN_PADDING, CLUSTER_DROPDOWN_TEXT_NUDGE, ENTRY_CORNER_RADIUS, FRAME_GAP, LOGGER, POS, SIZE, Pos, Size
from strings import STRINGS
from fonts import FONT
from widgets.dropdown import OverlaidButton, OverlaidRightAnchoredButton, bind_overlay
from widgets.misc import Tooltip
from helpers import resource_path, redraw_safe_size, list_clusters, get_cluster_details, get_cluster_error, get_shard_names

logger = logging.getLogger(LOGGER)

class WorldPanel(ctk.CTkScrollableFrame):
    """ Scrolling area built like the shard group it covers, so the two line up exactly. """

    RADIUS = 15

    def __init__(self, master, size):
        self.panel_width = size.w - self.RADIUS * 2
        self.panel_height = size.h - self.RADIUS

        super().__init__(
            master=master,
            width=self.panel_width,
            height=self.panel_height,
            fg_color=COLOR.GRAY,
            corner_radius=self.RADIUS,
            border_width=2,
            border_color=COLOR.GRAY_HOVER,
            scrollbar_button_color=COLOR.DARK_GRAY,
            scrollbar_button_hover_color=COLOR.DARK_GRAY,
        )

        self._scrollbar.configure(
            width=FRAME_GAP * 1.75,
            height=size.h * 0.25,
        )

    @property
    def content_width(self):
        """ Room the cards have, in unscaled pixels, next to the scrollbar. """

        return self.panel_width - FRAME_GAP / 2 - FRAME_GAP * 0.8

    @property
    def content_height(self):
        """ Height the cards can use before the panel has to scroll, in unscaled pixels. """

        return self.panel_height

    def _create_grid(self):
        super()._create_grid()

        pad = self._apply_widget_scaling(FRAME_GAP)

        self.configure(width=self.content_width)

        self._parent_canvas.grid(row=1, column=0, sticky="nsew", padx=(pad, 0), pady=pad)
        self._scrollbar.grid(row=1, column=1, sticky="nsew", pady=pad, padx=self._apply_widget_scaling(FRAME_GAP / 6))


class ClusterDropdown:
    """ Picks one of the clusters inside the Clusters Directory, from a panel of cards laid over the shards. """

    TEXT_PADDING = ENTRY_CORNER_RADIUS + CLUSTER_DROPDOWN_PADDING # CTkButton insets its text by the corner radius.
    TEXT_NUDGE = CLUSTER_DROPDOWN_TEXT_NUDGE
    BUTTON_RADIUS = ENTRY_CORNER_RADIUS
    ARROW_SIZE = 19.5
    ARROW_ROOM = 40
    MIN_BUTTON_WIDTH = 140

    CARD_RADIUS = 12
    CARD_PADDING = 16
    CARD_PADDING_Y = 10
    CARD_MIN_HEIGHT = 48
    CARD_TEXT_GAP = 2
    CARD_TEXT_ROOM = 24 # Between the text and the chips.
    CHIP_HEIGHT = 22
    CHIP_RADIUS = 11
    CHIP_GAP = 6
    RECENT_DAYS = 7 # Older than this, the last played day is shown as a date.

    def __init__(self, app, pos, size):
        self.app = app
        self.pos = pos
        self.size = size
        self.directory = None
        self.options = []
        self.selected_folder = None

        self._locked = False # True while the server runs.
        self._panel_open = False

        image = ctk.CTkImage(Image.open(resource_path("assets/dropdown.png")), size=(self.ARROW_SIZE, self.ARROW_SIZE))

        # The same button as the language dropdown, with the text drawn over it.
        self.button = OverlaidRightAnchoredButton(
            master=app,
            text="",
            command=self.toggle_menu,
            font=FONT.ENTRY,
            anchor="w",
            size=size,
            pos=pos,
            image=image,
            compound="right",
            corner_radius=self.BUTTON_RADIUS,
        )

        # Flat on the window until hovered, like the Local Files button on the console bar.
        self.button.configure(fg_color=COLOR.DARK_GRAY, hover_color=COLOR.MID_GRAY)
        self.button.show()

        self.name_label = self._create_label(self.button, COLOR.WHITE, FONT.CLUSTER_NAME)

        bind_overlay(self.button, self.name_label)

        # Explains why the world is invalid, like the entries do.
        self.tooltip = Tooltip(widget=self.button)
        self.tooltip.add_trigger(self.name_label)

        self.panel = WorldPanel(master=app, size=SIZE.SHARD_GROUP)

        # Dismiss the panel when clicking anywhere else.
        app.bind("<Button-1>", self._on_root_click, add="+")

        self._update_button()

    @staticmethod
    def _create_label(master, color, font=None):
        return ctk.CTkLabel(
            master=master,
            text="",
            height=0,
            width=0,
            anchor="w",
            fg_color="transparent",
            text_color=color,
            font=font or FONT.ENTRY,
        )

    # ------------------------------------------------------------------------------ #

    def get(self):
        """ Full path of the selected cluster, or an empty string. """

        if not self.directory or not self.selected_folder:
            return ""

        return (Path(self.directory) / self.selected_folder).as_posix()

    def set_directory(self, directory, load=False):
        """ Points the list at a clusters directory (None when it isn't usable), dropping the selection if it's gone. """

        options = list_clusters(directory) if directory else []

        if directory == self.directory and options == self.options:
            return

        self.directory = directory
        self.options = options

        folders = [folder for folder, _ in options]

        self.select(self.selected_folder if self.selected_folder in folders else None, load=load, force=True)

    def select(self, folder, load=False, force=False):
        if folder not in [option[0] for option in self.options]:
            folder = None

        changed = folder != self.selected_folder

        self.selected_folder = folder

        self.close_menu()
        self._update_button()
        self._set_valid(True)

        if changed or force:
            self._apply_selection(load)

        if changed and not load:
            self.app.save_entries_data()

    def validate_text(self):
        """ Whether a usable cluster is selected, flagging the field when it isn't. """

        reason = get_cluster_error(self.get())

        if reason:
            logger.info(f"The cluster selection is invalid: {reason}.")

        self._set_valid(reason is None, reason)

        return reason is None

    def enable(self):
        self._locked = False

        self._update_button()

    def disable(self):
        self._locked = True

        self.close_menu()
        self._update_button()

    # ------------------------------------------------------------------------------ #

    def _apply_selection(self, load):
        """ Loads what depends on the selected cluster: its token and its shards. """

        path = self.get()

        if get_cluster_error(path):
            self.app.shard_group.remove_all_shards()

            return

        directory_path = Path(path)

        token_file = directory_path / "cluster_token.txt"

        if token_file.exists():
            token = token_file.read_text(encoding="utf-8", errors="backslashreplace")

            self.app.token_entry.set_text(token, load=load)

        shard_names = get_shard_names(directory_path)
        single_shard = len(shard_names) == 1

        current_shards = list(self.app.shard_group.shards.keys())

        rebuild = current_shards != shard_names and not (single_shard and "PlaceHolder" in current_shards)

        if rebuild:
            self.app.shard_group.remove_all_shards()

            for shard_name in shard_names:
                self.app.shard_group.add_shard(code=shard_name)

            if single_shard:
                self.app.shard_group.add_placeholder_shard()
        else:
            for shard in self.app.shard_group.shards.values():
                shard.cleanup_state()

    def _set_valid(self, valid, reason=None):
        self.button.configure(
            border_width=0 if valid else 2,
            border_color=COLOR.RED,
        )

        self.tooltip.set_text(not valid and reason and STRINGS.ENTRY.INVALID_HELP[reason] or "")

    def _update_button(self):
        names = dict(self.options)

        if self.selected_folder:
            name, color = names[self.selected_folder], COLOR.WHITE

        elif self.directory and not self.options:
            name, color = STRINGS.CLUSTER_SELECT.EMPTY, COLOR.WHITE_HOVER

        else:
            name, color = STRINGS.CLUSTER_SELECT.PLACEHOLDER, COLOR.WHITE_HOVER

        name = FONT.CLUSTER_NAME.fit_text(name, self.size.w - self.TEXT_PADDING - self.ARROW_ROOM)

        self.name_label.configure(text=name, text_color=color)
        self.name_label.place(x=self.TEXT_PADDING, y=self.TEXT_NUDGE, rely=0.5, anchor="w")

        # The arrow is anchored to the button's right edge, so sizing the button to the text keeps it next to it.
        button_width = min(self.size.w, max(self.MIN_BUTTON_WIDTH, self.TEXT_PADDING + FONT.CLUSTER_NAME.text_width(name) + self.ARROW_ROOM))

        self.button.configure(width=redraw_safe_size(self.button, button_width))

        if self._can_open():
            self.button.enable()
        else:
            self.button.disable()

        self.name_label.configure(cursor="hand2" if self._can_open() else "no")

    def _can_open(self):
        return bool(self.options) and not self._locked

    # ------------------------------------------------------------------------------ #

    @staticmethod
    def _game_mode_text(game_mode):
        return STRINGS.CLUSTER_SELECT.GAME_MODE[game_mode.upper()] or game_mode.capitalize()

    @staticmethod
    def _mods_text(count):
        if count == 0:
            return STRINGS.CLUSTER_SELECT.NO_MODS

        return STRINGS.CLUSTER_SELECT.MODS_ONE if count == 1 else STRINGS.CLUSTER_SELECT.MODS_MANY.format(count=count)

    def _played_text(self, timestamp):
        if timestamp is None:
            return STRINGS.CLUSTER_SELECT.NEVER_PLAYED

        played = date.fromtimestamp(timestamp)
        days = (date.today() - played).days

        if days <= 0:
            return STRINGS.CLUSTER_SELECT.PLAYED_TODAY

        if days == 1:
            return STRINGS.CLUSTER_SELECT.PLAYED_YESTERDAY

        if days < self.RECENT_DAYS:
            return STRINGS.CLUSTER_SELECT.PLAYED_DAYS.format(count=days)

        return STRINGS.CLUSTER_SELECT.PLAYED_DATE.format(date=played.strftime("%x"))

    def _card_height(self, details):
        height = self.CARD_PADDING_Y * 2 + FONT.CLUSTER_NAME.line_height()

        if details.description:
            height += self.CARD_TEXT_GAP + FONT.ENTRY.line_height()

        return max(height, self.CARD_MIN_HEIGHT)

    def _build_cards(self):
        for child in self.panel.winfo_children():
            child.destroy()

        width = self.panel.content_width
        details = [get_cluster_details(self.directory, folder) for folder, _ in self.options]
        heights = [self._card_height(detail) for detail in details]

        gaps = FRAME_GAP * (len(details) - 1)

        # A few worlds would leave the panel mostly empty, so they share its whole height instead.
        fill = sum(heights) + gaps <= self.panel.content_height

        if fill:
            heights = [(self.panel.content_height - gaps) / len(details)] * len(details)

        for index, detail in enumerate(details):
            self._create_card(detail, width, heights[index], last=fill and index == len(details) - 1)

    def _create_card(self, details, width, height, last=False):
        name_height = FONT.CLUSTER_NAME.line_height()
        description_height = FONT.ENTRY.line_height()

        card = OverlaidButton(
            master=self.panel,
            text="",
            command=lambda folder=details.folder: self.select(folder),
            corner_radius=self.CARD_RADIUS,
            size=Size(width, height),
            pos=Pos(0, 0),
        )

        card.configure(fg_color=COLOR.DARK_GRAY, hover_color=COLOR.MID_GRAY)

        card.pack(fill="x", pady=(0, 0 if last else FRAME_GAP))

        # Info chips on the right, packed from the right edge inwards.
        texts = [self._game_mode_text(details.game_mode), self._played_text(details.last_played), self._mods_text(details.mods), details.folder]
        tips = [STRINGS.CLUSTER_SELECT.TOOLTIP.GAME_MODE, STRINGS.CLUSTER_SELECT.TOOLTIP.PLAYED, STRINGS.CLUSTER_SELECT.TOOLTIP.MODS, STRINGS.CLUSTER_SELECT.TOOLTIP.FOLDER]

        chips = ctk.CTkFrame(master=card, fg_color="transparent", corner_radius=0, width=0, height=self.CHIP_HEIGHT)
        chips.place(relx=1, x=-self.CARD_PADDING, rely=0.5, anchor="e")

        chip_labels = []
        chips_width = 0

        for text in reversed(texts):
            chip = ctk.CTkLabel(
                master=chips,
                text=text,
                width=0,
                height=self.CHIP_HEIGHT,
                corner_radius=self.CHIP_RADIUS,
                fg_color=COLOR.GRAY,
                text_color=COLOR.WHITE_HOVER,
                font=FONT.TOOLTIP_SMALL,
            )

            chip.pack(side="right", padx=(self.CHIP_GAP, 0))

            chip_labels.append(chip)
            chips_width += FONT.TOOLTIP_SMALL.text_width(text) + self.CHIP_RADIUS * 2 + self.CHIP_GAP

        text_width = width - self.CARD_PADDING * 2 - chips_width - self.CARD_TEXT_ROOM

        name_label = self._create_label(card, COLOR.WHITE, FONT.CLUSTER_NAME)
        name_label.configure(text=FONT.CLUSTER_NAME.fit_text(details.name, text_width))

        tinted = [name_label, chips]

        if details.description:
            # The two lines are centred as a block, which matters once the card is taller than its text.
            top = (height - name_height - self.CARD_TEXT_GAP - description_height) / 2

            name_label.place(x=self.CARD_PADDING, y=top, anchor="nw")

            description_label = self._create_label(card, COLOR.WHITE_HOVER)
            description_label.configure(text=FONT.ENTRY.fit_text(details.description, text_width))
            description_label.place(x=self.CARD_PADDING, y=top + name_height + self.CARD_TEXT_GAP, anchor="nw")

            tinted.append(description_label)
        else:
            name_label.place(x=self.CARD_PADDING, rely=0.5, anchor="w")

        bind_overlay(card, *tinted, backdrops=(chips, *chip_labels))

        for widget in (*tinted, *chip_labels):
            widget.configure(cursor="hand2")

        # Chips are packed from the right, so their texts are reversed.
        for chip, tip in zip(chip_labels, reversed(tips)):
            Tooltip(widget=chip, text=tip, above=True)

    # ------------------------------------------------------------------------------ #

    def _on_root_click(self, event):
        if not self._panel_open:
            return

        clicked = str(self.app.winfo_containing(event.x_root, event.y_root))

        if not clicked.startswith((str(self.panel._parent_frame), str(self.button))):
            self.close_menu()

    def toggle_menu(self, event=None):
        if self._panel_open:
            self.close_menu()

        elif self._can_open():
            self.tooltip.hide_tooltip()

            self._build_cards()

            self.panel.place(x=POS.SHARD_GROUP.x, y=POS.SHARD_GROUP.y)
            self.panel._parent_frame.lift()
            self.panel._parent_canvas.yview_moveto(0)

            self._panel_open = True

    def close_menu(self):
        self.panel.place_forget()

        self._panel_open = False
