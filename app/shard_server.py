import sys, os, psutil
import random
import logging, logging.config

from pathlib import Path
from io import TextIOWrapper

from pexpect import popen_spawn
from pexpect.exceptions import TIMEOUT, EOF

from constants import *
from helpers import *
from strings import STRINGS
from settings_manager import Settings

# ------------------------------------------------------------------------------------ #

logger = logging.getLogger(LOGGER)

PROCESS_ID = os.getpid()

# Log phrases that mark a boot step, in the order the server reaches them.
# Timings are from a clean local boot; mods and bigger worlds stretch MODS and ASSETS the most.
STARTING_STEPS = (
    ("LOADING LUA",                     "LOADING"),  # ~1s
    ("ModIndex: Beginning normal load", "MODS"   ),  # ~4s, runs twice (frontend, then sim)
    ("LOAD BE",                         "ASSETS" ),  # ~7-9s, longest phase
    ("Begin Session",                   "SESSION"),  # ~2-4s until the shard is online
)

# ------------------------------------------------------------------------------------ #

class StdoutMock(TextIOWrapper):
    def __init__(self) -> None:
        self.stdout = sys.stdout

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        sys.stdout = self.stdout

    def write(self, *args, **kwargs):
        pass


class DedicatedServerShard():
    def __init__(self, app, shard_frame) -> None:
        self.process = None
        self.task = None
        self.app = app
        self.starting_step = -1

        self.shard_frame = shard_frame
        self.shard = shard_frame.code

    def is_running(self):
        return self.process and self.process.proc.poll() is None or False

    def get_arguments(self, ugc_directory):
        game_directory    = Path(self.app.game_entry.get()   )
        cluster_directory = Path(self.app.cluster_entry.get())

        token = self.app.token_entry.get()

        cwd = (game_directory / "bin64").resolve()
        exe = (cwd / "dontstarve_dedicated_server_nullrenderer_x64").resolve()

        if not exe.with_suffix(".exe").exists():
            # Dev build executable.
            exe = (cwd / "dontstarve_dedicated_server_r_x64").resolve()

        paths = get_cluster_launch_paths(cluster_directory)

        args = [
            str(exe),
            "-cluster", paths["cluster"],
            "-shard", str(self.shard),
            "-monitor_parent_process", str(PROCESS_ID),
        ]

        if token:
            args.append("-token")
            args.append(token)
        else:
            logger.warning(f"({self.shard}) No token provided, the server will not be reachable online.")

        if paths["persistent_storage_root"]:
            args.append("-persistent_storage_root")
            args.append(paths["persistent_storage_root"])
        else:
            logger.warning(f"({self.shard}) Could not resolve the persistent storage root from '{cluster_directory}', the game will use its default one.")

        if paths["conf_dir"]:
            args.append("-conf_dir")
            args.append(paths["conf_dir"])
        else:
            logger.warning(f"({self.shard}) Could not resolve the config directory from '{cluster_directory}', the game will use its default one.")

        if paths["ownerdir"]:
            args.append("-ownerdir")
            args.append(paths["ownerdir"])

        if ugc_directory:
            args.append("-ugc_directory")
            args.append(ugc_directory)
        else:
            logger.warning(f"({self.shard}) No workshop directory found, subscribed mods will not be loaded.")

        args = args + split_launch_options(self.app.settings.get(Settings.LAUNCH_OPTIONS))

        return args, str(cwd)

    def resolve_ugc_directory(self):
        """ Workshop folder, from the game install when possible, otherwise from a previous launch's log. """

        ugc_directory = get_ugc_directory(self.app.game_entry.get())

        if ugc_directory:
            return ugc_directory

        launch_data = self.app.launch_data_save_loader.load()

        if launch_data is None and self.shard_frame.is_master:
            launch_data = retrieve_launch_data(self.app.cluster_entry.get(), self.app.launch_data_save_loader)

        return launch_data and launch_data["ugc_directory"] or None

    def start(self):
        if self.is_running():
            logger.warning(f"({self.shard}) Start request ignored, the shard is already running.")
            return

        game_directory_valid    = self.app.game_entry.validate_text()
        cluster_directory_valid = self.app.cluster_entry.validate_text()

        if not game_directory_valid or not cluster_directory_valid:
            if self.shard_frame.is_master:
                invalid_name = not game_directory_valid and STRINGS.ENTRY.GAME_TITLE or STRINGS.ENTRY.CLUSTER_TITLE
                self.app.error_popup.create(STRINGS.ERROR.DIRECTORY_INVALID.format(directory_name=invalid_name))

            logger.warning(f"({self.shard}) Start cancelled, the {not game_directory_valid and 'game' or 'cluster'} directory is invalid.")

            return

        ugc_directory = self.resolve_ugc_directory()

        if ugc_directory is None:
            if self.shard_frame.is_master:
                self.app.launch_data_popup.create(STRINGS.ERROR.LAUNCH_DATA_INVALID)

            logger.warning(f"({self.shard}) Start cancelled, the workshop directory could not be determined.")

            return

        logger.info(f"({self.shard}) Starting the shard...")

        self.starting_step = -1
        self.shard_frame.set_starting()

        args, cwd = self.get_arguments(ugc_directory)

        logger.info(f"({self.shard}) Launching from '{cwd}' with: {' '.join(redact_token(args))}")

        # This is HORRIBLE, but it works (Pyinstaller --noconcole + subprocess issue)
        try:
            with StdoutMock() as sys.stdout:
                self.process = popen_spawn.PopenSpawn(args, cwd=cwd, encoding="utf-8", codec_errors="ignore")
        except OSError as e:
            logger.error(f"({self.shard}) Failed to start the server process: {e}")

            self.shard_frame.set_offline()
            self.app.error_popup.create(STRINGS.ERROR.START_FAILED.format(shard=self.shard))

            return

        self.task = PeriodicTask(self.app, random.randrange(50, 70), self.handle_output, initial_time=0)

    def execute_command(self, command, log=True):
        if not self.is_running():
            return

        if log:
            logger.info(f"({self.shard}) Executing console command: {command}")

        try:
            self.process.sendline(command)

        except OSError as e:
            logger.error(f"({self.shard}) Failed to send the console command '{command}': {e}")

            self.app.error_popup.create(STRINGS.ERROR.COMMAND_FAILED.format(shard=self.shard))

    def on_stopped(self):
        logger.info(f"({self.shard}) The shard is now offline.")

        if self.task:
            self.task.kill()

        self.shard_frame.set_offline()

        self.process = None
        self.task = None

    def stop(self):
        if not self.is_running():
            return

        if self.shard_frame.is_starting() or self.shard_frame.is_restarting():
            logger.info(f"({self.shard}) Terminating the shard while it was still starting up.")

            try:
                if psutil.pid_exists(self.process.pid):
                    psutil.Process(self.process.pid).terminate()

            except psutil.NoSuchProcess:
                logger.debug(f"({self.shard}) The server process was already gone when terminating it.")

            self.on_stopped()
            self.app.stop_shards()

        elif self.shard_frame.is_online():
            logger.info(f"({self.shard}) Stopping the shard, waiting for the world to be saved...")

            self.shard_frame.set_stopping()

            self.execute_command(ANNOUNCE_STR.format(msg=STRINGS.COMMAND_ANNOUNCEMENT.SAVE_QUIT), log=False)
            self.execute_command(f"c_shutdown()")

    def handle_output(self):
        """
        Reads all new data from shard.process and handle key phases.
        Should be used in a PeriodicTask.

        Returns:
            success (bool, None): if not True, stops the loop. See PeriodicTask._execute.
            newtime: (int, float, None): override PeriodicTask.time for the next call, if not None. See PeriodicTask._execute.
        """

        if not self.is_running():
            self.on_stopped()
            self.app.stop_shards()

            return False, None

        text = None

        try:
            text = self.process.read_nonblocking(size=9999, timeout=None)

        except (EOF, TIMEOUT):
            return True, 500

        if not text:
            return True, None

        self.shard_frame.add_text_to_log_screen(text)

        self.handle_starting_progress(text=text)
        self.handle_output_keywords(text=text)

        if self.shard_frame.is_master:
            vox_data = read_vox_data(self.app.master_shard, text)

            if vox_data:
                self.app.cluster_stats.update(vox_data)

        return True, None

    def handle_starting_progress(self, text):
        """ A chunk can span several steps and some markers are logged again later, so only ever move forward. """

        if not self.shard_frame.is_starting():
            return

        for index, (phrase, step) in enumerate(STARTING_STEPS):
            if index > self.starting_step and phrase in text:
                self.starting_step = index
                self.shard_frame.set_starting_step(step)

                logger.debug(f"({self.shard}) Boot step reached: {step}.")

    def handle_output_keywords(self, text):
        if "[Shard] Stopping" in text:
            if not self.shard_frame.is_stopping():
                logger.info(f"({self.shard}) The shard is shutting down, stopping the other shards.")

            self.shard_frame.set_stopping()
            self.app.stop_shards()

        if "E_INVALID_TOKEN" in text or "E_EXPIRED_TOKEN" in text:
            logger.error(f"({self.shard}) The server rejected the token: it is invalid or has expired.")

            self.app.token_entry.toggle_warning(False, INVALID.TOKEN_REJECTED)
            self.app.stop_shards()

            self.app.error_popup.create(STRINGS.ERROR.TOKEN_INVALID)

        if "Received world rollback request" in text:
            logger.info(f"({self.shard}) A world rollback was requested, restarting every shard.")

            self.app.shard_group.set_all_shards_restarting()

        # A shard that was just told to stop must not flip back to online from the same chunk.
        if "uploads added to server." in text and self.is_running() and not self.shard_frame.is_stopping():
            if not self.shard_frame.is_online():
                logger.info(f"({self.shard}) The shard is now online!")

            self.shard_frame.set_online()

        if "SOCKET_PORT_ALREADY_IN_USE" in text:
            logger.error(f"({self.shard}) A server port is already in use, or the cluster path is wrong.")

            self.app.stop_shards()

            cluster_directory = Path(self.app.cluster_entry.get())
            ports = []

            for shard in get_shard_names(cluster_directory):
                config_file = cluster_directory / shard / "server.ini"

                if config_file.exists():
                    port = get_key_from_ini_file(config_file, "server_port")
                    ports.append(f"{port} ({STRINGS.SHARD_NAME[shard.upper()] or shard})")

            self.app.error_popup.create(STRINGS.ERROR.PORTS.format(ports=", ".join(ports)))

        if "[Error] Server failed to start!" in text:
            logger.error(f"({self.shard}) The server failed to start, see the shard logs for details.")

            self.app.stop_shards()

            self.app.error_popup.create(STRINGS.ERROR.GENERAL)

        if self.shard_frame.is_master and "Sim paused" in text:
            self.execute_command(load_lua_file("onserverpaused"), log=False)

        if "LUA ERROR stack traceback" in text:
            logger.warning(f"({self.shard}) The shard hit a Lua error, see the shard logs for the traceback.")

            self.app.error_popup.create(STRINGS.ERROR.SERVER_CRASH)