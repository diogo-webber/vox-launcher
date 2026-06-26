import logging, logging.config
import yaml
from functools import partial
from pathlib import Path
import traceback, requests
import subprocess, threading

from customtkinter import CTk, CTkLabel
from tkinter import StringVar, Toplevel

from constants import *
from helpers import *
from strings import STRINGS
from fonts import FONT
from settings_manager import SettingsManager, Settings

from widgets.buttons import CustomButton, ImageButton
from widgets.entries import TokenEntry, DirectoryEntry, ClusterDirectoryEntry
from widgets.frames import ScrollableShardGroupFrame
from widgets.misc import Tooltip, CommandPopUp, ServerErrorPopUp, AppExceptionPopUp, AppOutdatedPopUp, LaunchDataPopUp, ClusterStats, RestartRequiredPopUp
from widgets.settings_screen import SettingsScreen

# ------------------------------------------------------------------------------------ #

COLOR_FMT = "\u001b[1m\u001b[38;5;%dm"

COLOR_TERM = os.getenv("COLORTERM")
TERMINAL_SUPPORT_COLORS = COLOR_TERM is not None and COLOR_TERM.lower() in ('truecolor', '256color')

class CustomFormatter(logging.Formatter):
    """Logging Formatter to add colors to different levels"""

    blue   = COLOR_FMT % 69
    green  = COLOR_FMT % 71
    yellow = COLOR_FMT % 221
    red    = COLOR_FMT % 196

    #         [levelname]: message
    _format_colors = "{color}[%(levelname)s]:\u001b[0m \u001b[38;5;234m%(message)s\u001b[0m"
    _format_nocolors = "[%(levelname)s]: %(message)s"

    _format = TERMINAL_SUPPORT_COLORS and _format_colors or _format_nocolors

    FORMATTERS = {
        logging.DEBUG:    logging.Formatter(_format.format(color=blue    )),
        logging.INFO:     logging.Formatter(_format.format(color=green   )),
        logging.WARNING:  logging.Formatter(_format.format(color=yellow  )),
        logging.ERROR:    logging.Formatter(_format.format(color=red     )),
        logging.CRITICAL: logging.Formatter(_format.format(color=red     )),
    }

    def format(self, record):
        formatter = self.FORMATTERS.get(record.levelno)

        return formatter.format(record)

config_path = resource_path("logging_config.yaml")

with config_path.open('rt') as f:
    config = DotDict(yaml.safe_load(f.read()))

    logfile = resource_path(config.handlers.file.filename)
    config.handlers.file.filename = logfile

    config.formatters.console["()"] = CustomFormatter

    logfile.parent.mkdir(exist_ok=True, parents=True)

    logging.config.dictConfig(config.to_dict())


# ------------------------------------------------------------------------------------ #

GAME_DIR = get_game_directory()

GAME_INITIAL_DIR = GAME_DIR and GAME_DIR.parent or Path.home()
CLUSTER_INITIAL_DIR = get_clusters_directory()

DEBUG_MODE = LOGGER == "development"

# ------------------------------------------------------------------------------------ #

logger.info("Starting %s...", STRINGS.APP_NAME)
logger.info("App version: %s", APP_VERSION)
logger.info("Developer mode: %s", DEBUG_MODE)
logger.info("Assumed game folder: %s", GAME_DIR or "???")
logger.info("Assumed clusters folder: %s", CLUSTER_INITIAL_DIR or "???")

# ------------------------------------------------------------------------------------ #

class App(CTk):
    def __init__(self, **kwargs):
        super().__init__( **kwargs)

        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")

        screen_width  = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        x = (screen_width - WINDOW_WIDTH) // 2
        y = (screen_height - WINDOW_HEIGHT) // 2

        self.geometry(f"+{x}+{y}")

        self.settings = SettingsManager(app=self)
        self.settings.load()

        self.title(STRINGS.WINDOW_TITLE)
        self.iconbitmap(resource_path("assets/icon.ico"))
        self._set_appearance_mode("dark")
        self.configure(fg_color=COLOR.DARK_GRAY)

        self.resizable(False, False)

        self.entries_save_loader = SaveLoader(filename="entries.json")
        self.launch_data_save_loader = SaveLoader(filename="launchdata.json")

    def create_widgets(self):
        """
        Top section:
            - Game Directory selection
            - Cluster Directory selection
            - Dedicated server token input
        """

        self.game_entry = DirectoryEntry(
            master=self,
            tooltip=STRINGS.ENTRY.GAME_TITLE,
            validate_fn=validate_game_directory,
            initialdir=GAME_INITIAL_DIR,
            size=SIZE.DIRECTORY_ENTRY,
            pos=POS.GAME_DIRECTORY,
        )

        self.cluster_entry = ClusterDirectoryEntry(
            master=self,
            tooltip=STRINGS.ENTRY.CLUSTER_TITLE,
            validate_fn=validate_cluster_directory,
            initialdir=CLUSTER_INITIAL_DIR,
            size=SIZE.DIRECTORY_ENTRY,
            pos=POS.CLUSTER_DIRECTORY,
        )

        self.token_entry = TokenEntry(
            master=self,
            tooltip=STRINGS.ENTRY.TOKEN_TITLE,
            show="●",
            size=SIZE.TOKEN_ENTRY,
            pos=POS.TOKEN_ENTRY,
        )

        self.token_save_button = CustomButton(
            master=self,
            text="+",
            command=self.on_create_token_click,
            font=FONT.SMALL_BUTTON,
            size=SIZE.TOKEN_SAVE_BUTTON,
            pos=POS.TOKEN_SAVE_BUTTON,
            corner_radius=7,
        )

        self.token_save_button.show()

        self._save_token_tooltip = None
        self._save_token_tooltip_task = None

        self.token_save_button.bind("<Enter>", self._show_save_token_tooltip)
        self.token_save_button.bind("<Leave>", self._hide_save_token_tooltip)

        self.token_tooltip = Tooltip(
            master=self,
            text=STRINGS.TOKEN_TOOLTIP,
            image="assets/info.png",
            pos=POS.TOKEN_TOOLTIP,
            image_size=(SIZE.TOKEN_TOOLTIP.w, SIZE.TOKEN_TOOLTIP.h),
            onclick=open_klei_account_page,
        )

        # ---------------------------------------------------------------------- #

        """
        Middle section:
            - Cluster name
            - Cluster Stats
            - Shard Group
        """

        cluster_name_text = StringVar(value=STRINGS.CLUSTER_NAME_DEFAULT)

        self.cluster_name = CTkLabel(
            master=self,
            height=0,
            anchor="nw",
            textvariable=cluster_name_text,
            text_color=COLOR.WHITE,
            font=FONT.CLUSTER_NAME
        )

        self.cluster_name.text = cluster_name_text

        self.cluster_name.place(
            x=POS.CLUSTER_NAME.x,
            y=POS.CLUSTER_NAME.y
        )

        self.cluster_stats = ClusterStats(master=self)

        self.shard_group = ScrollableShardGroupFrame(
            master=self,
            color=COLOR.GRAY,
            size=SIZE.SHARD_GROUP,
            pos=POS.SHARD_GROUP,
        )

        # ---------------------------------------------------------------------- #

        """
            Bottom section:
            - Launch button
            - Console command buttons
            - Version label
        """

        launch_buton_text = StringVar(value=STRINGS.LAUNCH_BUTTON.LAUNCH)

        self.launch_button = CustomButton(
            master=self,
            textvariable=launch_buton_text,
            command=self.callback_launch,
            font=FONT.LAUNCH_BUTTON,
            size=SIZE.LAUNCH_BUTTON,
            pos=POS.LAUNCH_BUTTON,
        )

        self.launch_button.show()

        self.launch_button.text = launch_buton_text

        self.save_button = CustomButton(
            master=self,
            text=STRINGS.SMALL_BUTTON.SAVE,
            command=partial(self.execute_special_command, "c_save()", announcement=STRINGS.COMMAND_ANNOUNCEMENT.SAVE),
            font=FONT.SMALL_BUTTON,
            size=SIZE.SMALL_BUTTON,
            pos=POS.SAVE_BUTTON,
        )

        self.quit_button = CustomButton(
            master=self,
            text=STRINGS.SMALL_BUTTON.QUIT,
            command=partial(self.execute_special_command, "c_shutdown(false)", confirmation_text=STRINGS.COMMAND_CONFIRMATION.QUIT, announcement=STRINGS.COMMAND_ANNOUNCEMENT.QUIT),
            font=FONT.SMALL_BUTTON,
            size=SIZE.SMALL_BUTTON,
            pos=POS.QUIT_BUTTON,
        )

        self.reset_button = CustomButton(
            master=self,
            text=STRINGS.SMALL_BUTTON.RESET,
            command=partial(self.execute_special_command, "c_reset()", confirmation_text=STRINGS.COMMAND_CONFIRMATION.RESET, announcement=STRINGS.COMMAND_ANNOUNCEMENT.RESET),
            font=FONT.SMALL_BUTTON,
            size=SIZE.SMALL_BUTTON,
            pos=POS.RESET_BUTTON,
        )

        self.rollback_button = CustomButton(
            master=self,
            text=STRINGS.SMALL_BUTTON.ROLLBACK,
            command=partial(self.execute_special_command, load_lua_file("rollback_cmd"), announcement=STRINGS.COMMAND_ANNOUNCEMENT.ROLLBACK, slider_fn=rollback_slider_fn, confirmation_text=STRINGS.COMMAND_CONFIRMATION.ROLLBACK),
            font=FONT.SMALL_BUTTON,
            size=SIZE.SMALL_BUTTON,
            pos=POS.ROLLBACK_BUTTON,
        )

        self.confirmation_popup = CommandPopUp(root=self)
        self.error_popup = ServerErrorPopUp(root=self)
        self.exception_popup = AppExceptionPopUp(root=self)
        self.update_popup = AppOutdatedPopUp(root=self)
        self.launch_data_popup = LaunchDataPopUp(root=self)
        self.restart_popup = RestartRequiredPopUp(root=self)

        self.settings_screen = SettingsScreen(master=self)

        self.settings_button = ImageButton(
            master=self,
            image="assets/settings.png",
            command=self.settings_screen.show,
            width=SIZE.LOGS_BUTTON.w,
            height=SIZE.LOGS_BUTTON.h,
            image_size=(SIZE.LOGS_BUTTON.w - 20, SIZE.LOGS_BUTTON.h - 20),
            pos=Pos(WINDOW_MARGIN, WINDOW_HEIGHT - WINDOW_MARGIN - SIZE.LOGS_BUTTON.h)
        )

        self.settings_button.show()

        # ---------------------------------------------------------------------- #

        self.shard_group.remove_all_shards() # Initial state.
        self.load_saved_entries()

        if GAME_DIR and self.game_entry.get() == "":
            self.game_entry.set_text(GAME_DIR.as_posix(), load=True)

        # # Debug Stuff
        # self.save_button.show()
        # self.quit_button.show()
        # self.reset_button.show()
        # self.rollback_button.show()

        self.check_for_updates()

    def check_for_updates(self):
        def _check():
            try:
                response = requests.get(
                    url="https://github.com/diogo-webber/vox-launcher/releases/latest/",
                    timeout=5,
                )

                response.raise_for_status()  # Raise an exception for HTTP errors.

                remote_version = Path(response.url).name

                if response.status_code == 200 and remote_version != APP_VERSION[1:]:
                    self.after(300, self.update_popup.create, STRINGS.UPDATE_POPUP.DESCRIPTION.DEFAULT)

            except Exception:
                pass

        threading.Thread(target=_check, daemon=True).start()


    def callback_launch(self):
        if not hasattr(self, "master_shard"):
            return

        token = self.token_entry.get()

        if not token.strip():
            self.token_entry.toggle_warning(False)
            self.error_popup.create(STRINGS.ERROR.TOKEN_EMPTY)

            return # No token provided.

        if not is_valid_token(token):
            self.token_entry.toggle_warning(False)
            self.error_popup.create(STRINGS.ERROR.TOKEN_INVALID)

            return # Invalid token, don't start server.

        if self.master_shard.is_running():
            self.master_shard.stop()
        else:
            self.shard_group.start_all_shards()

    def on_create_token_click(self):
        cluster_dir = self.cluster_entry.get()

        if not cluster_dir:
            self.error_popup.create(STRINGS.ERROR.DIRECTORY_INVALID.format(directory_name=STRINGS.ENTRY.CLUSTER_TITLE))
            return

        directory_path = Path(cluster_dir)
        if not directory_path.exists():
            self.error_popup.create(STRINGS.ERROR.DIRECTORY_INVALID.format(directory_name=STRINGS.ENTRY.CLUSTER_TITLE))
            return

        token = self.token_entry.get()

        if not token.strip():
            self.token_entry.toggle_warning(False)
            self.error_popup.create(STRINGS.ERROR.TOKEN_EMPTY)
            return

        if not is_valid_token(token):
            self.token_entry.toggle_warning(False)
            self.error_popup.create(STRINGS.ERROR.TOKEN_INVALID)
            return

        token_file = directory_path / "cluster_token.txt"

        if token_file.exists():
            confirmed, _ = self.confirmation_popup.create(STRINGS.SAVE_TOKEN.OVERWRITE_CONFIRMATION)
        else:
            confirmed, _ = self.confirmation_popup.create(STRINGS.SAVE_TOKEN.CREATE_CONFIRMATION)

        if not confirmed:
            return

        try:
            token_file.write_text(token.strip(), encoding="utf-8")
            self.error_popup.create(STRINGS.SAVE_TOKEN.SUCCESS)
        except Exception as e:
            logging.getLogger(LOGGER).error("Failed to write cluster_token.txt: %s", e)
            self.error_popup.create(STRINGS.SAVE_TOKEN.SAVE_FAILED)

    def _show_save_token_tooltip(self, event=None):
        if self._save_token_tooltip_task:
            self.token_save_button.after_cancel(self._save_token_tooltip_task)
        self._save_token_tooltip_task = self.token_save_button.after(250, self._do_show_save_token_tooltip)

    def _do_show_save_token_tooltip(self):
        self.token_save_button.configure(cursor="hand2")
        self._save_token_tooltip = Toplevel(self.token_save_button)
        self._save_token_tooltip.wm_overrideredirect(True)

        label = CTkLabel(
            self._save_token_tooltip,
            text=STRINGS.SAVE_TOKEN.TOOLTIP,
            fg_color=COLOR.GRAY,
            bg_color=COLOR.DARK_GRAY,
            text_color=COLOR.WHITE,
            corner_radius=10,
            font=FONT.ENTRY,
            wraplength=350,
        )

        padding = label._apply_widget_scaling(18)
        label.pack(ipadx=padding, ipady=padding)

        try:
            label.update()
            x = self.token_save_button.winfo_rootx() - label.winfo_reqwidth() - label._apply_widget_scaling(36.67) - padding
            y = self.token_save_button.winfo_rooty() - label.winfo_reqheight() / 4 - label._apply_widget_scaling(5) - padding / 2
            self._save_token_tooltip.wm_geometry(f"+{round(x)}+{round(y)}")
        except Exception:
            self._save_token_tooltip = None

    def _hide_save_token_tooltip(self, event=None):
        self.token_save_button.configure(cursor="arrow")
        if self._save_token_tooltip_task:
            self.token_save_button.after_cancel(self._save_token_tooltip_task)
            self._save_token_tooltip_task = None
        if self._save_token_tooltip:
            self._save_token_tooltip.destroy()
            self._save_token_tooltip = None

    def execute_special_command(self, command, announcement=None, slider_fn=None, confirmation_text=None):
        if confirmation_text:
            confirmed, slider_value = self.confirmation_popup.create(confirmation_text, slider_fn=slider_fn)

            if confirmed:
                command_fmt = slider_value and command.format(value=slider_value) or command

                if announcement:
                    self.master_shard.execute_command(ANNOUNCE_STR.format(msg=announcement), log=False)

                self.master_shard.execute_command(command_fmt)

        else:
            if announcement:
                self.master_shard.execute_command(ANNOUNCE_STR.format(msg=announcement), log=False)

            self.master_shard.execute_command(command)


    def save_entries_data(self):
        logger.debug("Entries data has been saved.")

        self.entries_save_loader.save(
            token       =  self.token_entry.get(),
            game_dir    = self.game_entry.get(),
            cluster_dir = self.cluster_entry.get(),
        )

    def load_saved_entries(self):
        logger.info("Entries data has been imported.")

        data = self.entries_save_loader.load()

        if not data:
            return

        self.token_entry.set_text(data.token, load=True)
        self.game_entry.set_text(data.game_dir, load=True)
        self.cluster_entry.set_text(data.cluster_dir, load=True)

    def stop_shards(self):
        self.shard_group.stop_all_shards()

    def restart_application(self, *args, **kwargs):
        """Restart the PyInstaller-exe or Python script safely."""
        logger.info("Restarting the application.")

        try:
            # Restart the process and exit the current instance.
            subprocess.Popen([sys.executable] + sys.argv, close_fds=True)
        except OSError:
            logger.error("Failed to restart via sys.executable, trying sys.argv[0].")

            try:
                subprocess.Popen(sys.argv, close_fds=True)
            except OSError:
                logger.error("Failed to restart the application.")
                return

        self.destroy() # Close the windows before exiting program.
        sys.exit(0)

    def report_callback_exception(self, exctype, excvalue, tb): # Overrides Ctk method.
        err: list = traceback.format_exception(exctype, excvalue, tb)
        error = " ".join(err)

        logger.error(error)

        summary = f'{exctype.__name__}: {excvalue}.'

        self.stop_shards()

        self.exception_popup.create(STRINGS.ERROR.EXCEPTION.format(error=summary), error)


# ------------------------------------------------------------------------------------ #

if __name__ == "__main__":
    #set_debug_scale(1)

    app = App()

    STRINGS.load_strings(app.settings.get(Settings.LANGUAGE))
    FONT.create_fonts() # Needs to run after string loading.

    # ------------------------------------------------------------------------------------ #

    app.create_widgets()

    if DEBUG_MODE:
        app.bind("<Control-r>", app.restart_application)

    app.mainloop()
