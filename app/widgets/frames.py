from customtkinter import CTkFrame, CTkLabel, CTkTextbox, CTkEntry, CTkButton, CTkSwitch, CTkScrollableFrame, CTkImage
from tkinter import StringVar, END, CENTER, DISABLED, NORMAL, BOTH
import re, logging
from pathlib import Path
from PIL import Image

from strings import STRINGS
from constants import APP_VERSION, COLOR, SERVER_STATUS, OFFSET, SIZE, FRAME_GAP, FONT_SIZE, LOGGER, Pos, Size
from widgets.buttons import RelativeXImageButton, CustomButton
from helpers import load_lua_file, get_readable_system_language, disable_bind, resource_path, get_memory_usage, open_folder, TextHightlightData, PeriodicTask
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

        image_size = self.root._apply_widget_scaling(12)
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
            columnspan=3,
            padx=(65, 0),
            sticky="nw",
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
            #sticky="n",
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
            ipady=FONT_SIZE.CLUSTER_STATS / 3,
            sticky="n",
        )

        value_label.grid(
            row = 0,
            column = column + 1,
            ipady=FONT_SIZE.CLUSTER_STATS / 3,
            sticky="n",
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


class ShardLogPanel():
    switch_xpad = 20

    def __init__(self, master, shard, server) -> None:
        self.server = server
        self.master = master
        self.bind = None
        self._auto_scroll = False
        self._visible = False
        self.shard = shard
        self.corner_radius = 10
        self.hightlight_data = []

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

        #self.textbox.bind("<MouseWheel>", self._mouse_scroll_event)

        self.textbox._textbox.configure(selectbackground=COLOR.GRAY)

        self.add_hightlight(pattern=r'\[\d{2}:\d{2}:\d{2}\]:', name="timestamp", color=COLOR.CONSOLE_GRAY)
        self.add_hightlight(pattern=r'World \d* is now connected', name="online", color=COLOR.GREEN)
        self.add_hightlight(pattern=r'RemoteCommandInput:.*?[\n\r]+', name="remotecommand", color=COLOR.LIGHT_BLUE)
        #self.add_hightlight(pattern=r'\[Warning\].*?[\n\r]+', name="warnings", color=COLOR.YELLOW) # FIXME: bugged

        self.textbox.place(
            x = OFFSET.LOGS_TEXTBOX.x,
            y = OFFSET.LOGS_TEXTBOX.y,
        )

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

        # self.show_end_button = ImageButton(
        #     master=self.root,
        #     image="assets/arrowdown.png",
        #     bg_color=COLOR.DARK_GRAY,
        #     command=self.show_end,
        #     width=SIZE.LOGS_SHOW_END_BUTTON.w,
        #     height=SIZE.LOGS_SHOW_END_BUTTON.h,
        #     image_size=(SIZE.LOGS_SHOW_END_BUTTON.w - 18, SIZE.LOGS_SHOW_END_BUTTON.h - 18),
        #     pos=Pos(OFFSET.LOGS_SHOW_END_BUTTON.x, OFFSET.LOGS_SHOW_END_BUTTON.y),
        # )

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

        self.bind = self.master.bind("<Escape>", self.hide)

        self.root.lift()
        self.highlight_text()

        if self.server.is_running():
            self.show_end()

            self.topbar.start_tracking_memory()

        elif not self.textbox.get("1.0", END).strip(): # If empty.
            log_path = Path(self.server.app.cluster_entry.get()) / self.shard / "server_log.txt"

            if log_path.exists():
                self.reset_text()
                self.append_text(log_path.read_text(encoding="utf-8"))

                logger.debug(f"Loading log file for {self.shard}.")


    def hide(self, *args, **kwargs):
        if self.master.grab_current() is not None:
            return # Not in focus...

        self._visible = False
        self.root.place_forget()

        self.topbar.stop_tracking_memory()

        if self.bind:
            self.master.unbind("<Escape>", self.bind)
            self.bind = None

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
            self.entry.delete(0, END)
            self.show_end()

    def append_text(self, text):
        self.textbox.configure(state=NORMAL) # To be able to insert text!
        self.textbox.insert(END, text)
        self.textbox.configure(state=DISABLED)

        if self._visible:
            self.highlight_text()

            if self._auto_scroll:
                self.show_end()

            else:
                self._mouse_scroll_event()

    def reset_text(self):
        self.textbox.configure(state=NORMAL) # To be able to delete text!
        self.textbox.delete("1.0", END)
        self.textbox.configure(state=DISABLED)

    def show_end(self):
        self.textbox.see(END)
        self._mouse_scroll_event()

    def add_hightlight(self, pattern, name, color):
        self.textbox.tag_config(name, foreground=color)

        self.hightlight_data.append(
            TextHightlightData(
                pattern = re.compile(pattern),
                name = name,
            )
        )

    def highlight_text(self):
        text = self.textbox.get("1.0", END)

        for highlight in self.hightlight_data:
            self.textbox.tag_remove(highlight.name, "1.0", END)

            matches = highlight.pattern.finditer(text)

            for match in matches:
                start, end = match.span()
                self.textbox.tag_add(highlight.name, f"1.0+{start}c", f"1.0+{end}c")

    def _mouse_scroll_event(self, *args, **kwargs):
        pass
    #     if self.textbox.yview()[1] > 0.995:
    #         self.show_end_button.hide()
    #     else:
    #         self.show_end_button.show()

    def _auto_scroll_event(self):
        self._auto_scroll = self.auto_scroll_switch.get()

        if self._auto_scroll:
            self.show_end()

        else:
            pass
            #self._mouse_scroll_event()


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
            anchor="nw",
            textvariable=self.status_msg,
            text_color=COLOR.WHITE,
            fg_color="transparent",
            font=FONT.SHARD_STATUS,
        )

        self.status_msg_label.place(
            relx = 0.84,
            y = OFFSET.SHARD_STATUS_MSG.y,
        )

        self.set_offline()

    def set_offline(self):
        self.status.set(SERVER_STATUS.OFFLINE)

        self.status_msg.set(STRINGS.SHARD_STATUS.OFFLINE)
        self.status_circle.set_color(COLOR.WHITE)

        if self.is_master:
            self._master.launch_button.update(
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
            self._master.launch_button.update(
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
            self._master.launch_button.update(
                text=STRINGS.LAUNCH_BUTTON.CANCEL,
                fg_color=COLOR.RED,
                hover_color=COLOR.RED_HOVER,
            )

            self._master.game_entry.disable()
            self._master.cluster_entry.disable()
            self._master.token_entry.disable()

    def set_stopping(self):
        self.status.set(SERVER_STATUS.STOPPING)

        self.status_msg.set(STRINGS.SHARD_STATUS.STOPPING)
        self.status_circle.set_color(COLOR.YELLOW)

        if self.is_master:
            self._master.launch_button.update(
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
            self._master.launch_button.update(text=STRINGS.LAUNCH_BUTTON.SAVE_QUIT)

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

        self.hightlight_data = []

        self.tag_config("hightlight", foreground=COLOR.GREEN)

        for pattern in STRINGS.CLUSTER_GROUP_TOOLTIP_HIGHLIGHT_PATTERNS:
            self.add_hightlight(pattern=pattern)

        self.highlight_text()

        self._textbox.configure(selectbackground=COLOR.GRAY)

        self.configure(state=DISABLED, spacing3=self._apply_widget_scaling(20))

        self.bind("<MouseWheel>", disable_bind)


    def add_hightlight(self, pattern):
        self.hightlight_data.append(
            TextHightlightData(
                pattern = re.compile(pattern),
                name = "hightlight",
            )
        )

    def highlight_text(self):
        text = self.get("1.0", END)

        for highlight in self.hightlight_data:
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

        if relx and y:
            self.place(relx=relx, y=y - size/2)

    def set_color(self, color):
        self.configure(
            fg_color = color,
            border_color = color,
        )