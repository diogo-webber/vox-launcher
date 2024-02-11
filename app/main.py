import logging, logging.config
import yaml
from pathlib import Path

from customtkinter import CTk, CTkLabel
from tkinter import StringVar

from constants import *
from helpers import *
from strings import STRINGS
from fonts import Fonts

from widgets.buttons import CustomButton
from widgets.entries import TokenEntry, DirectoryEntry, ClusterDirectoryEntry
from widgets.frames import ScrollableShardGroupFrame
from widgets.misc import Tooltip, PopUp, ClusterStats

# ------------------------------------------------------------------------------------ #

COLOR_FMT = "\u001b[1m\u001b[38;5;%dm"

class CustomFormatter(logging.Formatter):
    """Logging Formatter to add colors to different levels"""

    blue     = COLOR_FMT % 69
    green    = COLOR_FMT % 71
    yellow   = COLOR_FMT % 221
    red = COLOR_FMT % 196

    #         [levelname]: message
    _format = "{color}[%(levelname)s]:\u001b[0m \u001b[38;5;234m%(message)s\u001b[0m"

    FORMATTERS = {
        logging.DEBUG:    logging.Formatter(_format.format(color=blue    )),
        logging.INFO:     logging.Formatter(_format.format(color=green    )),
        logging.WARNING:  logging.Formatter(_format.format(color=yellow  )),
        logging.ERROR:    logging.Formatter(_format.format(color=red     )),
        logging.CRITICAL: logging.Formatter(_format.format(color=red)),
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

# ------------------------------------------------------------------------------------ #

logger.info("Starting %s...", STRINGS.APP_NAME)
logger.info("App version: %s", APP_VERSION)
logger.info("Developer mode: %s", LOGGER == "development")
logger.info("Assumed game folder: %s", GAME_DIR or "???")
logger.info("Assumed clusters folder: %s", CLUSTER_INITIAL_DIR or "???")

# ------------------------------------------------------------------------------------ #

class App(CTk):
    def __init__(self, **kwargs):
        super().__init__( **kwargs)

        self.geometry( f"{ WINDOW_WIDTH }x{ WINDOW_HEIGHT }" )
        self.title(STRINGS.WINDOW_TITLE)
        self.iconbitmap(resource_path("assets/icon.ico"))
        self._set_appearance_mode("dark")
        self.configure(fg_color=COLOR.DARK_GRAY)

        self.resizable(False, False)

        self.entries_save_loader = SaveLoader(filename="entries.json")

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
            image_size=(SIZE.TOKEN_TOOLTIP.w - 5, SIZE.TOKEN_TOOLTIP.h - 5),
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
            command=self.create_console_command_fn("c_save()", announcement=STRINGS.COMMAND_ANNOUNCEMENT.SAVE),
            font=FONT.SMALL_BUTTON,
            size=SIZE.SMALL_BUTTON,
            pos=POS.SAVE_BUTTON,
        )

        self.quit_button = CustomButton(
            master=self,
            text=STRINGS.SMALL_BUTTON.QUIT,
            command=self.create_console_command_fn("c_shutdown(false)", confirmation_text=STRINGS.COMMAND_CONFIRMATION.QUIT, announcement=STRINGS.COMMAND_ANNOUNCEMENT.QUIT),
            font=FONT.SMALL_BUTTON,
            size=SIZE.SMALL_BUTTON,
            pos=POS.QUIT_BUTTON,
        )

        self.reset_button = CustomButton(
            master=self,
            text=STRINGS.SMALL_BUTTON.RESET,
            command=self.create_console_command_fn("c_reset()", confirmation_text=STRINGS.COMMAND_CONFIRMATION.RESET, announcement=STRINGS.COMMAND_ANNOUNCEMENT.RESET),
            font=FONT.SMALL_BUTTON,
            size=SIZE.SMALL_BUTTON,
            pos=POS.RESET_BUTTON,
        )

        self.rollback_button = CustomButton(
            master=self,
            text=STRINGS.SMALL_BUTTON.ROLLBACK,
            command=self.create_console_command_fn(load_lua_file("rollback_cmd"), announcement=STRINGS.COMMAND_ANNOUNCEMENT.ROLLBACK, slider_fn=rollback_slider_fn, confirmation_text=STRINGS.COMMAND_CONFIRMATION.ROLLBACK),
            font=FONT.SMALL_BUTTON,
            size=SIZE.SMALL_BUTTON,
            pos=POS.ROLLBACK_BUTTON,
        )

        self.confirmation_popup = PopUp(root=self)

        self.version_label = CTkLabel(
            master=self,
            height=0,
            anchor="sw",
            text=STRINGS.VERSION_LABEL,
            text_color=COLOR.WHITE,
            font=FONT.VERSION,
        )

        self.version_label.place(
            x = WINDOW_MARGIN,
            y = WINDOW_HEIGHT - WINDOW_MARGIN - FONT_SIZE.VERSION,
        )

        # ---------------------------------------------------------------------- #

        self.shard_group.remove_all_shards() # Initial state.
        self.load_saved_entries()

        if GAME_DIR and self.game_entry.get() == "":
            self.game_entry.set_text(GAME_DIR.as_posix(), load=True)


    def callback_launch(self):
        if not hasattr(self, "master_shard"):
            return

        if self.master_shard.is_running():
            self.master_shard.stop()
        else:
            self.shard_group.start_all_shards()


    def create_console_command_fn(self, command, announcement=None, slider_fn=None, confirmation_text=None):
        def ret():
            if confirmation_text:
                confirmed, slider_value = self.confirmation_popup.create(confirmation_text, slider_fn)

                if confirmed:
                    command_fmt = slider_value and command.format(value=slider_value) or command

                    if announcement:
                        self.master_shard.execute_command(ANNOUNCE_STR.format(msg=announcement), log=False)

                    self.master_shard.execute_command(command_fmt)

            else:
                if announcement:
                    self.master_shard.execute_command(ANNOUNCE_STR.format(msg=announcement), log=False)

                self.master_shard.execute_command(command)

        return ret


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

# ------------------------------------------------------------------------------------ #

if __name__ == "__main__":
    app = App()

    FONT = Fonts()

    # ------------------------------------------------------------------------------------ #

    app.create_widgets()
    app.mainloop()
