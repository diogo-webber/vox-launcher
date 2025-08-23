import sys
import os
import logging, logging.config
import yaml
from functools import partial
from pathlib import Path
import traceback, requests
import subprocess

# Define CustomFormatter before any logging configuration
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

from customtkinter import CTk, CTkLabel
from tkinter import StringVar

from discord_handler import DiscordWebhookHandler

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

# Set up logging configuration
def setup_logging():
    config_path = resource_path("logging_config.yaml")
    
    with config_path.open('rt') as f:
        config_dict = yaml.safe_load(f.read())

        # Convert file paths
        logfile = resource_path(config_dict["handlers"]["file"]["filename"])
        config_dict["handlers"]["file"]["filename"] = str(logfile)

        # Set up custom formatter using the class object directly
        config_dict["formatters"]["console"]["()"] = CustomFormatter

        # Set up Discord webhook if configured
        settings_manager = SettingsManager(enum_cls=Settings, app=None)
        settings_manager.load()
        webhook_url = settings_manager.get_setting(Settings.DISCORD_WEBHOOK)
        game_logs_only = settings_manager.get_setting(Settings.DISCORD_GAME_LOGS_ONLY)
        
        # Remove Discord handler if no webhook URL is configured
        if not webhook_url:
            for logger_name in ["development", "production"]:
                if "discord" in config_dict["loggers"][logger_name]["handlers"]:
                    config_dict["loggers"][logger_name]["handlers"].remove("discord")
        else:
            config_dict["handlers"]["discord"]["webhook_url"] = webhook_url
            config_dict["handlers"]["discord"]["game_logs_only"] = game_logs_only

        logfile.parent.mkdir(exist_ok=True, parents=True)

        # Apply the configuration
        logging.config.dictConfig(config_dict)

setup_logging()

# Now we can set up the logger
logger = logging.getLogger(LOGGER)


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

        self.settings = SettingsManager(app=self, enum_cls=Settings)
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

        self.settings_screen = SettingsScreen(master=app)

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
        try:
            response = requests.get(
                url="https://github.com/diogo-webber/vox-launcher/releases/latest/",
                timeout=5,
            )

            response.raise_for_status()  # Raise an exception for HTTP errors.

            remote_version = Path(response.url).name

            if response.status_code == 200 and remote_version != APP_VERSION[1:]:
                self.after(300, self.update_popup.create, STRINGS.UPDATE_POPUP.DESCRIPTION.DEFAULT)

        except:
            pass


    def callback_launch(self):
        if not hasattr(self, "master_shard"):
            return

        if not is_valid_token(self.token_entry.get()):
            self.token_entry.toggle_warning(False)
            self.error_popup.create(STRINGS.ERROR.TOKEN_INVALID)

            return # Invalid token, don't start server.

        if self.master_shard.is_running():
            self.master_shard.stop()
        else:
            self.shard_group.start_all_shards()

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

        # Restart the process and exit the current instance.
        subprocess.Popen([sys.executable] + sys.argv, close_fds=True)

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

    STRINGS.load_strings(app.settings.get_setting(Settings.LANGUAGE))
    FONT.create_fonts() # Needs to run after string loading.

    # ------------------------------------------------------------------------------------ #

    app.create_widgets()

    if DEBUG_MODE:
        app.bind("<Control-r>", app.restart_application)

    app.mainloop()
