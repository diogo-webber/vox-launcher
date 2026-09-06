from customtkinter import CTkFrame, CTkLabel, CTkTextbox, CTkEntry, CTkButton, CTkSwitch, CTkScrollableFrame, CTkImage
from tkinter import StringVar, END, CENTER, DISABLED, NORMAL, BOTH
import re, logging
from pathlib import Path
from PIL import Image

from strings import STRINGS, get_readable_system_language
from constants import APP_VERSION, COLOR, SERVER_STATUS, OFFSET, SIZE, FRAME_GAP, FONT_SIZE, LOGGER, Pos, Size
from widgets.buttons import RelativeXImageButton, ImageButton, CustomButton
from helpers import load_lua_file, disable_bind, resource_path, get_memory_usage, open_folder, TextHighlightData, PeriodicTask, read_file_nonblocking
from shard_server import DedicatedServerShard
from fonts import FONT

logger = logging.getLogger(LOGGER)

class LogsTopBar:
    def __init__(self, master, server, shard) -> None:
        self.root = master
        self.server = server
        self.shard = shard
        self.memory = StringVar(value="--")

        self._frame = CustomFrame(
            master=self.root,
            color=COLOR.GRAY,
            size=SIZE.LOGS_TOP_BAR,
            pos=OFFSET.LOGS_TOP_BAR,
        )

        # CTkFrame shrinks to its children, which would pull the row above the bar's centre.
        self._frame.grid_propagate(False)
        self._frame.grid_rowconfigure(0, weight=1)

        image_size = 17

        image = CTkImage(Image.open(resource_path("assets/directory.png")), size=(image_size, image_size))

        self.open_folder_button = CustomButton(
            master=self._frame,
            text=STRINGS.LOG_SCREEN.SHARD_FOLDER,
            command=self._open_shard_folder,
            font=FONT.CLUSTER_STATS,
            size=Size(100, 20),
            pos=Pos(0, 0),
            image=image,
        )

        self.open_folder_button.grid(
            row = 0,
            column = 5,
            padx=(65, 0),
        )

        self.status_circle = ColouredCircle(
            master=self._frame,
            color=COLOR.WHITE,
            size = SIZE.SHARD_STATUS_CIRCLE.w - 4,
        )

        self.status_circle.grid(
            row = 0,
            column = 0,
            padx=(15, 10),
        )

        self.shard_name   = self.create_label(text=STRINGS.SHARD_NAME[self.shard.upper()] or self.shard, title=STRINGS.LOG_SCREEN.SHARD_NAME_TITLE, column=1)
        self.memory_label = self.create_label(textvariable=self.memory, title=STRINGS.LOG_SCREEN.SHARD_MEMORY_TITLE, column=3)

    def create_label(self, title, column, textvariable=None, text=None):
        title_label =  CTkLabel(
            master=self._frame,
            height=0,
            anchor="center",
            text=title,
            text_color=COLOR.WHITE,
            font=FONT.CLUSTER_STATS,
        )

        value_label =  CTkLabel(
            master=self._frame,
            height=0,
            anchor="center",
            text=text,
            textvariable=textvariable,
            text_color=COLOR.WHITE_HOVER,
            font=FONT.CLUSTER_STATS,
        )

        title_label.grid(
            row = 0,
            column = column,
            padx=(column == 1 and FRAME_GAP * 1.5 or 65, 10),
        )

        value_label.grid(
            row = 0,
            column = column + 1,
        )

    def update_memory(self):
        if not self.server.is_running():
            self.memory.set("--")

            return True, None

        memory, memory_percent = get_memory_usage(pid=self.server.process.pid)

        if not (memory and memory_percent):
            return True, None

        memory_mb = memory / 1000 / 1000

        self.memory.set(STRINGS.LOG_SCREEN.SHARD_MEMORY_FMT.format(mb=round(memory_mb, 2), percent=round(memory_percent)))

        return True, None

    def _open_shard_folder(self):
        open_folder(Path(self.server.app.cluster_entry.get()) / self.shard)

    def start_tracking_memory(self):
        self.update_memory()
        self.memory_task = PeriodicTask(self.root, time=2500, func=self.update_memory)

    def stop_tracking_memory(self):
        task = getattr(self, "memory_task", None)

        if isinstance(task, PeriodicTask):
            self.memory_task.kill()
            self.memory_task = None

            self.memory.set("--")

    def show(self):
        self._frame.place(
            x=OFFSET.LOGS_TOP_BAR.x,
            y=OFFSET.LOGS_TOP_BAR.y,
        )

    def hide(self):
        self._frame.place_forget()


class LogSearchBar:
    """ Find bar floating over the log textbox, toggled with Ctrl+F. """

    MATCH_TAG = "search_match"
    CURRENT_TAG = "search_current"

    MIN_TERM_LENGTH = 2
    MAX_MATCHES = 2000

    def __init__(self, panel) -> None:
        self.panel = panel
        self.textbox = panel.textbox
        self.matches = []
        self.index = -1
        self.visible = False

        self.term = StringVar()
        self.counter = StringVar(value=STRINGS.LOG_SCREEN.SEARCH_NO_RESULTS)

        # Configured after the syntax highlights so they win on the lines they share.
        self.textbox.tag_config(self.MATCH_TAG, background=COLOR.GRAY_HOVER, foreground=COLOR.BLUE)
        self.textbox.tag_config(self.CURRENT_TAG, background=COLOR.BLUE, foreground=COLOR.DARK_GRAY)

        self._frame = CustomFrame(
            master=panel.root,
            color=COLOR.GRAY,
            bg_color=COLOR.DARK_GRAY,
            border_color=COLOR.GRAY_HOVER,
            border_width=1,
            size=SIZE.LOGS_SEARCH_BAR,
            corner_radius=10,
        )

        self._frame.grid_propagate(False)
        self._frame.grid_rowconfigure(0, weight=1)

        # Absorbs the slack so the buttons stay pinned to the right edge.
        self._frame.grid_columnconfigure(1, weight=1)

        self.entry = CTkEntry(
            master=self._frame,
            corner_radius=8,
            border_width=0,
            fg_color=COLOR.DARK_GRAY,
            text_color=COLOR.WHITE,
            font=FONT.ENTRY_ARIAL,
            width=SIZE.LOGS_SEARCH_ENTRY.w,
            height=SIZE.LOGS_SEARCH_ENTRY.h,
            textvariable=self.term,
        )

        self.entry._entry.configure(selectbackground=COLOR.GRAY_HOVER)

        self.entry.grid(row=0, column=0, padx=(FRAME_GAP, 8))

        self.entry.bind("<Return>", lambda event: self.go_to_match(1))
        self.entry.bind("<Shift-Return>", lambda event: self.go_to_match(-1))
        self.entry.bind("<Escape>", self.hide)

        self.term.trace_add("write", self.run_search)

        self.count_label = CTkLabel(
            master=self._frame,
            height=0,
            width=0,
            anchor="e",
            textvariable=self.counter,
            text_color=COLOR.WHITE_HOVER,
            font=FONT.SEARCH_RESULTS,
        )

        self.count_label.grid(row=0, column=1, padx=(0, 8), sticky="ew")

        self.divider = CustomFrame(
            master=self._frame,
            color=COLOR.GRAY_HOVER,
            size=SIZE.LOGS_SEARCH_DIVIDER,
            corner_radius=0,
        )

        self.divider.grid(row=0, column=2, padx=(0, 6))

        arrow = Image.open(resource_path("assets/arrowdown.png"))
        close = Image.open(resource_path("assets/close.png"))

        icon_size = SIZE.LOGS_SEARCH_BUTTON.h - 10
        icon = (icon_size, icon_size)

        self.previous_button = self._create_button(CTkImage(arrow.rotate(180), size=icon), 3, lambda: self.go_to_match(-1))
        self.next_button     = self._create_button(CTkImage(arrow,             size=icon), 4, lambda: self.go_to_match(1) )
        self.close_button    = self._create_button(CTkImage(close,             size=icon), 5, self.hide                    )

    def _create_button(self, image, column, command):
        button = CustomButton(
            master=self._frame,
            text="",
            image=image,
            command=command,
            corner_radius=6,
            size=SIZE.LOGS_SEARCH_BUTTON,
            pos=Pos(0, 0),
        )

        # CustomButton hardcodes its colors, so they can only be overridden afterwards.
        button.configure(fg_color="transparent", hover_color=COLOR.GRAY_HOVER)

        button.grid(row=0, column=column, padx=(0, column == 5 and FRAME_GAP or 4))

        return button

    def show(self, *args, **kwargs):
        if not self.visible:
            self.visible = True

            self._frame.place(x=OFFSET.LOGS_SEARCH_BAR.x, y=OFFSET.LOGS_SEARCH_BAR.y)
            self._frame.lift()

            self.run_search()

        self.entry.focus_set()

        return "break"

    def hide(self, *args, **kwargs):
        if not self.visible:
            return "break"

        self.visible = False

        self._frame.place_forget()

        self.textbox.tag_remove(self.MATCH_TAG, "1.0", END)
        self.textbox.tag_remove(self.CURRENT_TAG, "1.0", END)

        self.matches = []
        self.index = -1

        return "break"

    def run_search(self, *args):
        term = self.term.get()

        self.textbox.tag_remove(self.MATCH_TAG, "1.0", END)
        self.textbox.tag_remove(self.CURRENT_TAG, "1.0", END)

        self.matches = []
        self.index = -1

        if len(term) >= self.MIN_TERM_LENGTH:
            start = "1.0"

            while len(self.matches) < self.MAX_MATCHES:
                position = self.textbox._textbox.search(term, start, stopindex=END, nocase=True)

                if not position:
                    break

                end = f"{position}+{len(term)}c"

                self.textbox.tag_add(self.MATCH_TAG, position, end)
                self.matches.append((position, end))

                start = end

        if self.matches:
            self.go_to_match(1)
        else:
            self.update_counter()

    def go_to_match(self, step):
        if not self.matches:
            return "break"

        self.index = (self.index + step) % len(self.matches)

        start, end = self.matches[self.index]

        self.textbox.tag_remove(self.CURRENT_TAG, "1.0", END)
        self.textbox.tag_add(self.CURRENT_TAG, start, end)
        self.textbox.see(start)

        self.update_counter()

        return "break"

    def update_counter(self):
        if not self.matches:
            self.counter.set(STRINGS.LOG_SCREEN.SEARCH_NO_RESULTS)

            return

        self.counter.set(STRINGS.LOG_SCREEN.SEARCH_RESULTS.format(index=self.index + 1, total=len(self.matches)))


class ShardLogPanel():
    switch_xpad = 20
    max_history = 50

    def __init__(self, master, shard, server) -> None:
        self.server = server
        self.master = master
        self.bind = None
        self.search_bind = None
        self._auto_scroll = False
        self._visible = False
        self.shard = shard
        self.corner_radius = 10
        self.highlight_data = []
        self._highlight_end = "1.0"
        self._history = []
        self._history_index = 0

        self.root = CustomFrame(
            master=master,
            color=COLOR.GRAY,
            size=SIZE.LOGS_PANEL,
            #pos=OFFSET.LOGS_PANEL,
            corner_radius=self.corner_radius,
        )

        self.topbar = LogsTopBar(master=self.root, server=self.server, shard=self.shard)

        self.textbox = CTkTextbox(
            master = self.root,
            width = SIZE.LOGS_TEXTBOX.w,
            height = SIZE.LOGS_TEXTBOX.h,
            corner_radius = self.corner_radius,
            fg_color = COLOR.DARK_GRAY,
            text_color = COLOR.WHITE,
            scrollbar_button_color = COLOR.GRAY,
            scrollbar_button_hover_color = COLOR.GRAY_HOVER,
            font = FONT.TEXTBOX_ARIAL,
            state = DISABLED,
        )

        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>", "<ButtonRelease-1>", "<Prior>", "<Next>"):
            self.textbox.bind(sequence, self._mouse_scroll_event)

        scrollbar = getattr(self.textbox, "_y_scrollbar", None)

        if scrollbar is not None:
            scrollbar.bind("<B1-Motion>", self._mouse_scroll_event)

        self.textbox._textbox.configure(selectbackground=COLOR.GRAY)

        self.add_highlight(pattern=r'\[\d{2}:\d{2}:\d{2}\]:', name="timestamp", color=COLOR.CONSOLE_GRAY)
        self.add_highlight(pattern=r'World \d* is now connected', name="online", color=COLOR.GREEN)
        self.add_highlight(pattern=r'RemoteCommandInput:.*?[\n\r]+', name="remotecommand", color=COLOR.LIGHT_BLUE)
        self.add_highlight(pattern=r'\[Warning\].*?[\n\r]+', name="warnings", color=COLOR.YELLOW)
        self.add_highlight(pattern=r'(?<=\[\d{2}:\d{2}:\d{2}\]: )(\[string ".*?)(?=\[\d{2}:\d{2}:\d{2}\]:|\Z)', name="crash", color="#e88a84", flags=re.DOTALL)

        self.textbox.place(
            x = OFFSET.LOGS_TEXTBOX.x,
            y = OFFSET.LOGS_TEXTBOX.y,
        )

        self.search_bar = LogSearchBar(self)

        self.entry = CTkEntry(
            master = self.root,
            corner_radius=self.corner_radius,
            border_color=COLOR.DARK_GRAY,
            text_color=COLOR.WHITE,
            fg_color=COLOR.DARK_GRAY,
            font=FONT.ENTRY,
            border_width=0,
            width=SIZE.LOGS_ENTRY.w,
            height=SIZE.LOGS_ENTRY.h,
            placeholder_text=STRINGS.LOG_SCREEN.ENTRY_PLACEHOLDER.format(shard=STRINGS.SHARD_NAME[self.shard.upper()] or self.shard),
        )

        self.entry._entry.configure(selectbackground=COLOR.GRAY)

        self.entry.place(
            x = OFFSET.LOGS_ENTRY.x,
            y = OFFSET.LOGS_ENTRY.y,
        )

        self.entry.bind("<Return>", self.execute_command)
        self.entry.bind("<Up>", lambda event: self.browse_history(-1))
        self.entry.bind("<Down>", lambda event: self.browse_history(1))

        self.button = CTkButton(
            master=self.root,
            text=STRINGS.LOG_SCREEN.CLOSE,
            command=self.hide,
            corner_radius=10,
            fg_color=COLOR.RED,
            hover_color=COLOR.RED_HOVER,
            text_color=COLOR.WHITE,
            width=SIZE.LOGS_CLOSE.w,
            height=SIZE.LOGS_CLOSE.h,
            font=FONT.LAUNCH_BUTTON,
            border_width=1,
            border_color=COLOR.DARK_GRAY,
        )

        self.button.place(
            x = OFFSET.LOGS_CLOSE.x,
            y = OFFSET.LOGS_CLOSE.y,
        )

        self.show_end_button = ImageButton(
            master=self.root,
            image="assets/arrowdown.png",
            bg_color=COLOR.DARK_GRAY,
            command=self.show_end,
            corner_radius=8,
            width=SIZE.LOGS_SHOW_END_BUTTON.w,
            height=SIZE.LOGS_SHOW_END_BUTTON.h,
            # CTkButton reserves corner_radius on both sides, so the icon has to fit in what is left.
            image_size=(SIZE.LOGS_SHOW_END_BUTTON.w - 17, SIZE.LOGS_SHOW_END_BUTTON.h - 17),
            pos=Pos(OFFSET.LOGS_SHOW_END_BUTTON.x, OFFSET.LOGS_SHOW_END_BUTTON.y),
        )

        self.auto_scroll_switch = CTkSwitch(
            master=self.root,
            text=STRINGS.LOG_SCREEN.AUTO_SCROLL,
            command=self._auto_scroll_event,
            onvalue=True,
            offvalue=False,
            bg_color=COLOR.GRAY,
            fg_color=COLOR.DARK_GRAY,
            progress_color=COLOR.GREEN,
            button_color=COLOR.WHITE,
            button_hover_color=COLOR.WHITE,
            text_color=COLOR.WHITE,
            font=FONT.TEXTBOX,
            width=SIZE.LOGS_AUTO_SCROLL_SWITCH.w + self.switch_xpad,
            height=SIZE.LOGS_AUTO_SCROLL_SWITCH.h,
        )

        self.auto_scroll_switch.place(
            x = OFFSET.LOGS_AUTO_SCROLL_SWITCH.x - self.switch_xpad,
            y = OFFSET.LOGS_AUTO_SCROLL_SWITCH.y,
        )

        self.auto_scroll_switch._canvas.grid(    row=0, column=0, sticky="",  padx=(self.switch_xpad, 10))
        self.auto_scroll_switch._text_label.grid(row=0, column=2, sticky="w", padx=(0, self.switch_xpad))

        self.hide()

        self.server.shard_frame.add_status_change_callback(self.on_server_status_changed)

    def show(self, *args, **kwargs):
        self._visible = True

        self.root.place(
            x=OFFSET.LOGS_PANEL.x,
            y=OFFSET.LOGS_PANEL.y,
        )

        self.bind = self.master.bind("<Escape>", self.on_escape)
        self.search_bind = self.master.bind("<Control-f>", self.search_bar.show)

        self.root.lift()
        self.highlight_text()
        self._mouse_scroll_event()

        if self.server.is_running():
            self.show_end()

            self.topbar.start_tracking_memory()

        elif not self.textbox.get("1.0", END).strip():
            # Using after() to safely update UI from main thread.
            read_file_nonblocking(
                Path(self.server.app.cluster_entry.get()) / self.shard / "server_log.txt",
                lambda text: self.root.after(0, self.on_load_log_file, text)
            )

            self.reset_text()

            logger.debug(f"Loading log file for {self.shard}.")


    def on_escape(self, *args, **kwargs):
        """ Escape backs out of the search bar first, then out of the panel. """

        if self.search_bar.visible:
            return self.search_bar.hide()

        self.hide()

    def hide(self, *args, **kwargs):
        if self.master.grab_current() is not None:
            return # Not in focus...

        self._visible = False

        self.search_bar.hide()
        self.root.place_forget()

        self.topbar.stop_tracking_memory()

        if self.bind:
            self.master.unbind("<Escape>", self.bind)
            self.bind = None

        if self.search_bind:
            self.master.unbind("<Control-f>", self.search_bind)
            self.search_bind = None

    def on_server_status_changed(self, *args):
        if self.server.shard_frame.is_starting():
            self.reset_text()

            # Needs to enable it before setting the string.
            self.entry.configure(state=NORMAL)
            self.entry.configure(placeholder_text=STRINGS.LOG_SCREEN.ENTRY_PLACEHOLDER.format(shard=STRINGS.SHARD_NAME[self.shard.upper()] or self.shard))

            self.topbar.status_circle.set_color(COLOR.YELLOW)

        elif self.server.shard_frame.is_stopping() or self.server.shard_frame.is_restarting():
            self.topbar.status_circle.set_color(COLOR.YELLOW)

        elif self.server.shard_frame.is_online():
            self.topbar.status_circle.set_color(COLOR.GREEN)

        elif self.server.shard_frame.is_offline():
            # Needs to set the string before disabling it.
            self.entry.delete(0, END)
            self.entry.configure(placeholder_text=STRINGS.LOG_SCREEN.ENTRY_PLACEHOLDER_OFFLINE)
            self.entry.configure(state=DISABLED)

            self.topbar.stop_tracking_memory()

            self.topbar.status_circle.set_color(COLOR.WHITE)

    def execute_command(self, *args, **kwargs):
        command = self.entry.get()

        if command and self.server:
            self.server.execute_command(command)
            self.push_history(command)
            self.entry.delete(0, END)
            self.show_end()

    def push_history(self, command):
        if not self._history or self._history[-1] != command:
            self._history.append(command)

            del self._history[:-self.max_history]

        self._history_index = len(self._history)

    def browse_history(self, step):
        """ Walks the sent commands, where the slot past the end is the empty line. """

        if not self._history:
            return "break"

        self._history_index = max(0, min(len(self._history), self._history_index + step))

        self.entry.delete(0, END)

        if self._history_index < len(self._history):
            self.entry.insert(0, self._history[self._history_index])

        return "break"

    def append_text(self, text):
        self.textbox.configure(state=NORMAL) # To be able to insert text!
        self.textbox.insert(END, text)
        self.textbox.configure(state=DISABLED)

        if self._visible:
            self.highlight_text(incremental=True)

            if self._auto_scroll:
                self.show_end()

            else:
                self._mouse_scroll_event()

    def append_text_from_file(self, text):
        # Cancel any ongoing insert
        if hasattr(self, "_append_job"):
            self.root.after_cancel(self._append_job)

        self.textbox.configure(state=NORMAL)

        MAX_LINES = 10000

        self._append_lines = text.splitlines(keepends=True)
        self._append_index = 0

        if len(self._append_lines) > MAX_LINES:
            logger.info(f"Truncating log file for shard '{self.shard}' because it exceeds the maximum allowed {MAX_LINES} lines.")

            truncation_message = (
                f">> This log has been truncated to the last {MAX_LINES} lines.\n\n"
            )

            # Keep only the last MAX_LINES lines and prepend the message
            self._append_lines = [truncation_message] + self._append_lines[-MAX_LINES:]

        # Reset highlight while we're inserting
        for h in self.highlight_data:
            self.textbox.tag_remove(h.name, "1.0", END)

        self._append_next_chunk()

    def _append_next_chunk(self):
        if self._append_index >= len(self._append_lines):
            self._append_lines = []
            self._append_index = 0

            # Final scroll and highlight
            if self._visible:
                self.highlight_text()
                if self._auto_scroll:
                    self.show_end()
                else:
                    self._mouse_scroll_event()

            self.textbox.configure(state=DISABLED)

            logger.debug(f"Loaded log file for {self.shard}.")

            return

        text = ''.join(self._append_lines[self._append_index : self._append_index + 500])

        start_idx = self.textbox.index(END)
        self.textbox.insert(END, text)
        self._highlight_range(start_idx, text)

        self._append_index += 500
        self._append_job = self.root.after(1, self._append_next_chunk)

    def reset_text(self):
        self.textbox.configure(state=NORMAL) # To be able to delete text!
        self.textbox.delete("1.0", END)
        self.textbox.configure(state=DISABLED)
        self._highlight_end = "1.0"

        self.search_bar.run_search() # The matches point into text that is gone now.

    def on_load_log_file(self, text=None):
        if text and not self.server.is_running():
            self.reset_text()
            self.append_text_from_file(text)

    def show_end(self):
        self.textbox.see(END)
        self._mouse_scroll_event()

    def add_highlight(self, pattern, name, color, flags=0):
        self.textbox.tag_config(name, foreground=color)

        self.highlight_data.append(
            TextHighlightData(
                pattern = re.compile(pattern, flags=flags),
                name = name,
            )
        )

    def _char_to_index(self, text, char_pos, base_line=1, base_col=0):
        prefix = text[:char_pos]
        newlines = prefix.count('\n')

        if newlines == 0:
            return f"{base_line}.{base_col + char_pos}"

        last_newline = prefix.rfind('\n')
        col = char_pos - last_newline - 1
        return f"{base_line + newlines}.{col}"

    def _highlight_range(self, start_idx, text):
        parts = str(start_idx).split('.')
        base_line = int(parts[0])
        base_col = int(parts[1])

        for highlight in self.highlight_data:
            if highlight.pattern.flags & re.DOTALL:
                continue

            for match in highlight.pattern.finditer(text):
                s, e = match.span()
                self.textbox.tag_add(
                    highlight.name,
                    self._char_to_index(text, s, base_line, base_col),
                    self._char_to_index(text, e, base_line, base_col),
                )

    def highlight_text(self, incremental=False):
        if incremental:
            start = self._highlight_end
            text = self.textbox.get(start, END)

            if not text.strip():
                return

            self._highlight_range(self.textbox.index(start), text)
            self._highlight_end = self.textbox.index(END)
            return

        text = self.textbox.get("1.0", END)

        for highlight in self.highlight_data:
            self.textbox.tag_remove(highlight.name, "1.0", END)

            for match in highlight.pattern.finditer(text):
                s, e = match.span()
                self.textbox.tag_add(
                    highlight.name,
                    self._char_to_index(text, s),
                    self._char_to_index(text, e),
                )

        self._highlight_end = self.textbox.index(END)

    def _mouse_scroll_event(self, *args, **kwargs):
        # yview() still reports the old position while the scroll event is being handled.
        self.root.after_idle(self._update_show_end_button)

    def _update_show_end_button(self):
        if not self._visible:
            return

        if self.textbox._textbox.yview()[1] > 0.999:
            self.show_end_button.hide()
        else:
            self.show_end_button.show()

    def _auto_scroll_event(self):
        self._auto_scroll = self.auto_scroll_switch.get()

        if self._auto_scroll:
            self.show_end()

        else:
            self._mouse_scroll_event()


class CustomFrame(CTkFrame):
    def __init__(self, color, size, pos=None, corner_radius=15, border_color=None, bg_color="transparent", **kwargs):
        super().__init__(
            border_color=border_color or color,
            fg_color=color,
            bg_color = bg_color,
            corner_radius=corner_radius,
            width=size.w,
            height=size.h,
            **kwargs
        )

        if pos:
            self.place(
                x=pos.x,
                y=pos.y,
            )


class PlaceHolderShardFrame(CustomFrame):
    def __init__(self,**kwargs):
        super().__init__(
            color=COLOR.DARK_GRAY,
            size=SIZE.FRAME,
            **kwargs
        )

        self.text = CTkLabel(
            master=self,
            height=0,
            text=STRINGS.SHARD_NAME.EMPTY,
            text_color=COLOR.GRAY_HOVER,
            fg_color="transparent",
            font=FONT.SHARD_STATUS,
        )

        self.text.place(
            relx = 0.5,
            rely = 0.5,
            anchor=CENTER,
        )

    def cleanup_state(self):
        pass


class ShardFrame(CustomFrame):
    def __init__(self, app, master, code, size, first=False, **kwargs):
        self.status = StringVar(value=SERVER_STATUS.OFFLINE)
        self.code = code
        self.is_master = None
        self._master = app

        super().__init__(
            master=master,
            size=size,
            bg_color=COLOR.GRAY,
            **kwargs
        )

        self.pack(pady=(not first and FRAME_GAP or 0, 0), fill=BOTH)
        self.status_msg = StringVar(value=STRINGS.SHARD_STATUS.OFFLINE)

        self.type = CTkLabel(
            master=self,
            height=0,
            anchor="nw",
            text=STRINGS.SHARD_NAME[code.upper()] or self.code,
            text_color=COLOR.WHITE,
            fg_color="transparent",
            font=FONT.SHARD_TYPE,
        )

        self.type.place(
            relx= 0.05,
            y= OFFSET.SHARD_TYPE.y,
        )

        self.server = DedicatedServerShard(self._master, self)
        self.shard_log_panel = ShardLogPanel(master=app, shard=code, server=self.server)

        self.logs = RelativeXImageButton(
            master=self,
            image="assets/console.png",
            command=self.shard_log_panel.show,
            width=SIZE.LOGS_BUTTON.w,
            height=SIZE.LOGS_BUTTON.h,
            image_size=(SIZE.LOGS_BUTTON.w - 20, SIZE.LOGS_BUTTON.h - 20),
            relx=0.68,
            y=OFFSET.LOGS_BUTTON.y,
        )

        self.logs.show()

        self.status_circle = ColouredCircle(
            master=self,
            color=COLOR.WHITE,
            relx = 0.80,
            y = OFFSET.SHARD_STATUS_CIRCLE.y,
            size = SIZE.SHARD_STATUS_CIRCLE.w,
        )

        self.status_msg_label = CTkLabel(
            master=self,
            height=0,
            anchor="w",
            textvariable=self.status_msg,
            text_color=COLOR.WHITE,
            fg_color="transparent",
            font=FONT.SHARD_STATUS,
        )

        # The label box keeps the font's descender empty below the text, so centring it alone reads high.
        self.status_msg_label.place(
            relx = 0.84,
            y = OFFSET.SHARD_STATUS_CIRCLE.y + FONT.SHARD_STATUS.metrics("descent") / 4,
            anchor = "w",
        )

        self.set_offline()

    def set_offline(self):
        self.status.set(SERVER_STATUS.OFFLINE)

        self.status_msg.set(STRINGS.SHARD_STATUS.OFFLINE)
        self.status_circle.set_color(COLOR.WHITE)

        if self.is_master:
            self._master.launch_button.set_style(
                text=STRINGS.LAUNCH_BUTTON.LAUNCH,
                fg_color=COLOR.GRAY,
                hover_color=COLOR.GRAY_HOVER,
            )

            self._master.launch_button.enable()

            self._master.save_button.hide()
            self._master.quit_button.hide()
            self._master.reset_button.hide()
            self._master.rollback_button.hide()

            self._master.cluster_stats.hide()

            self._master.game_entry.enable()
            self._master.cluster_entry.enable()
            self._master.token_entry.enable()

    def set_restarting(self):
        self.status.set(SERVER_STATUS.RESTARTING)

        self.status_msg.set(STRINGS.SHARD_STATUS.RESTARTING)
        self.status_circle.set_color(COLOR.YELLOW)

        if self.is_master:
            self._master.launch_button.set_style(
                text=STRINGS.LAUNCH_BUTTON.CANCEL,
                fg_color=COLOR.RED,
                hover_color=COLOR.RED_HOVER,
            )

            self._master.save_button.hide()
            self._master.quit_button.hide()
            self._master.reset_button.hide()
            self._master.rollback_button.hide()


    def set_starting(self):
        self.status.set(SERVER_STATUS.STARTING)

        self.status_msg.set(STRINGS.SHARD_STATUS.STARTING)
        self.status_circle.set_color(COLOR.YELLOW)

        if self.is_master:
            self._master.launch_button.set_style(
                text=STRINGS.LAUNCH_BUTTON.CANCEL,
                fg_color=COLOR.RED,
                hover_color=COLOR.RED_HOVER,
            )

            self._master.game_entry.disable()
            self._master.cluster_entry.disable()
            self._master.token_entry.disable()

    def set_starting_step(self, step):
        """ Refines the STARTING message as the shard reaches each boot step. """

        if self.is_starting():
            self.status_msg.set(STRINGS.SHARD_STATUS.STEP[step] or STRINGS.SHARD_STATUS.STARTING)
    def set_stopping(self):
        self.status.set(SERVER_STATUS.STOPPING)

        self.status_msg.set(STRINGS.SHARD_STATUS.STOPPING)
        self.status_circle.set_color(COLOR.YELLOW)

        if self.is_master:
            self._master.launch_button.set_style(
                text=STRINGS.LAUNCH_BUTTON.STOPPING,
                fg_color=COLOR.GRAY,
                hover_color=COLOR.GRAY_HOVER,
            )

            self._master.launch_button.disable()

            self._master.save_button.hide()
            self._master.quit_button.hide()
            self._master.reset_button.hide()
            self._master.rollback_button.hide()

            self._master.cluster_stats.hide()

    def set_online(self):
        self.status.set(SERVER_STATUS.ONLINE)

        self.status_msg.set(STRINGS.SHARD_STATUS.ONLINE)
        self.status_circle.set_color(COLOR.GREEN)

        if self.is_master:
            self._master.launch_button.set_style(text=STRINGS.LAUNCH_BUTTON.SAVE_QUIT)

            self._master.save_button.show()
            self._master.quit_button.show()
            self._master.reset_button.show()
            self._master.rollback_button.show()

            self._master.master_shard.execute_command(load_lua_file("worlddata", version=APP_VERSION, lang_code=get_readable_system_language()), log=False)

    def is_starting(self):
        return self.status.get() == SERVER_STATUS.STARTING

    def is_online(self):
        return self.status.get() == SERVER_STATUS.ONLINE

    def is_stopping(self):
        return self.status.get() == SERVER_STATUS.STOPPING

    def is_restarting(self):
        return self.status.get() == SERVER_STATUS.RESTARTING

    def is_offline(self):
        return self.status.get() == SERVER_STATUS.OFFLINE

    def add_text_to_log_screen(self, text):
        self.shard_log_panel.append_text(text)

    def add_status_change_callback(self, cb):
        self.status.trace_add("write", cb)

    def cleanup_state(self):
        self.shard_log_panel.reset_text()


class TextBoxAsLabel(CTkTextbox):
    def __init__(self, master):
        super().__init__(
            master = master,
            width = SIZE.SHARD_GROUP.w - 10,
            height = SIZE.SHARD_GROUP.h + 5,
            corner_radius = 15,
            fg_color = COLOR.GRAY,
            text_color = COLOR.WHITE,
            activate_scrollbars=False,
            font = FONT.SHARD_TOOLTIP,
            border_spacing=30,
        )

        self.insert("1.0", STRINGS.CLUSTER_GROUP_TOOLTIP)

        self.highlight_data = []

        self.tag_config("highlight", foreground=COLOR.GREEN)

        for pattern in STRINGS.CLUSTER_GROUP_TOOLTIP_HIGHLIGHT_PATTERNS:
            self.add_highlight(pattern=pattern)

        self.highlight_text()

        self._textbox.configure(selectbackground=COLOR.GRAY)

        self.configure(state=DISABLED, spacing3=self._apply_widget_scaling(20))

        self.bind("<MouseWheel>", disable_bind)


    def add_highlight(self, pattern):
        self.highlight_data.append(
            TextHighlightData(
                pattern = re.compile(pattern),
                name = "highlight",
            )
        )

    def highlight_text(self):
        text = self.get("1.0", END)

        for highlight in self.highlight_data:
            matches = highlight.pattern.finditer(text)

            for match in matches:
                start, end = match.span()
                self.tag_add(highlight.name, f"1.0+{start}c", f"1.0+{end}c")


class ScrollableShardGroupFrame(CTkScrollableFrame):
    def __init__(self, master, color, pos, size, corner_radius=15, border_color=None, bg_color="transparent", **kwargs):
        self.pos = pos

        self.shards = {}
        self.app = master

        self._width = size.w - (corner_radius * 2)
        self._height = size.h - corner_radius

        super().__init__(
            master=master,
            border_color=border_color or color,
            fg_color=color,
            bg_color = bg_color,
            corner_radius=corner_radius,
            width=self._width,
            height=self._height,
            border_width=0,
            scrollbar_button_color=COLOR.DARK_GRAY,
            scrollbar_button_hover_color=COLOR.DARK_GRAY,
            **kwargs
        )

        self._scrollbar.configure(
            width  = FRAME_GAP * 1.75,
            height = size.h * 0.25,
        )

        self.place(
            x=self.pos.x,
            y=self.pos.y,
        )

        self.tooltip = TextBoxAsLabel(master=master)

    def add_shard(self, code):
        is_master = code == "Master"

        self.shards[code] = ShardFrame(
            app = self.app,
            master=self,
            code=code,
            color=COLOR.DARK_GRAY,
            size=SIZE.FRAME,
            first=is_master,
        )

        if is_master:
            self.shards[code].is_master = True

            self.app.master_shard = self.shards[code].server

            self.hide_tooltip()

            self.app.launch_button.enable()

        self._create_grid()

        # Nasty way of fixing a visual bug.
        self.after(50, self._parent_canvas.yview_moveto, 1)
        self.after(50, self._parent_canvas.yview_moveto, 0)

    def add_placeholder_shard(self):
        self.shards["PlaceHolder"] = PlaceHolderShardFrame(master=self)

        self.shards["PlaceHolder"].pack(pady=(FRAME_GAP, 0), fill=BOTH)

        self._create_grid()

        # Nasty way of fixing a visual bug.
        self.after(50, self._parent_canvas.yview_moveto, 1)
        self.after(50, self._parent_canvas.yview_moveto, 0)

    def remove_all_shards(self):
        for frame in self.get_shards(include_placeholders=True):
            frame.destroy()

            if hasattr(frame, "shard_log_panel"):
                frame.shard_log_panel.root.destroy()

        self.shards = {}

        self.show_tooltip()

        self.app.launch_button.disable()

    def start_all_shards(self):
        for frame in self.get_shards():
            frame.server.start()

    def stop_all_shards(self):
        for frame in self.get_shards():
            frame.server.stop()

    def set_all_shards_restarting(self):
        for frame in self.get_shards():
            frame.set_restarting()

    def get_shards(self, include_placeholders=False):
        if include_placeholders:
            return self.shards.values()

        return [v for k, v in self.shards.items() if k != "PlaceHolder"]

    def show_tooltip(self):
        self.tooltip.place(
            x=self.pos.x,
            y=self.pos.y,
        )

        self.place_forget()

    def hide_tooltip(self):
        self.tooltip.place_forget()

        self.place(
            x=self.pos.x,
            y=self.pos.y,
        )

    def _create_grid(self):
        super()._create_grid()

        pad = self._apply_widget_scaling(FRAME_GAP)

        if len(self.shards) <= 2:
            self._parent_canvas.grid(row=1, column=0, sticky="nsew", padx=pad, pady=pad)
            self._scrollbar.grid_forget()

            self.configure(width=self._width)

            return

        self.configure(width=self._width - FRAME_GAP / 2 - FRAME_GAP * 0.8)

        self._parent_canvas.grid(row=1, column=0, sticky="nsew", padx=(pad, 0), pady=pad)
        self._scrollbar.grid(row=1, column=1, sticky="nsew", pady = self._apply_widget_scaling(FRAME_GAP), padx= self._apply_widget_scaling(FRAME_GAP / 6))


class ColouredCircle(CTkFrame):
    def __init__(self, color, size, relx=None, y=None, **kwargs):
        super().__init__(
            border_color=color,
            fg_color=color,
            corner_radius=360,
            height=size,
            width=size,
            **kwargs)

        if relx is not None and y is not None:
            self.place(relx=relx, y=y - size/2)

    def set_color(self, color):
        self.configure(
            fg_color = color,
            border_color = color,
        )