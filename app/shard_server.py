import logging

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
        self.app = app

        self.shard_frame = shard_frame
        self.shard = shard_frame.code

    def is_running(self):
        return self.process and self.process.proc.poll() is None or False

    def get_arguments(self, launch_data):
        game_directory    = Path(self.app.game_entry.get()   )
        cluster_directory = Path(self.app.cluster_entry.get())

        token = self.app.token_entry.get()
        cluster = get_cluster_name(cluster_directory)

        cwd = (game_directory / "bin64").resolve()
        exe = (cwd / "dontstarve_dedicated_server_nullrenderer_x64").resolve()

        if not exe.with_suffix(".exe").exists():
            # Dev build executable.
            exe = (cwd / "dontstarve_dedicated_server_r_x64").resolve()

        args = f"""
            {exe}
            -cluster {cluster}
            -shard {self.shard}
            -monitor_parent_process {PROCESS_ID}
            -token {token}
        """

        args = args.split()

        if launch_data.ownerdir:
            args.append("-ownerdir")
            args.append(launch_data.ownerdir)
        else:
            logger.warning("Starting shard: missing user dir.")

        if launch_data.persistent_storage_root:
            args.append("-persistent_storage_root")
            args.append(launch_data.persistent_storage_root)
        else:
            logger.warning("Starting shard: missing storage root.")

        if launch_data.ugc_directory:
            args.append("-ugc_directory")
            args.append(launch_data.ugc_directory)
        else:
            logger.warning("Starting shard: missing mods directory.")

        extra_args = self.app.settings.get_setting(Settings.LAUNCH_OPTIONS).split()

        args = args + extra_args

        return args, str(cwd)

    def start(self):
        if self.is_running():
            logger.warning(f"Shard {self.shard} is already running...")
            return

        game_directory_valid    = self.app.game_entry.validate_text()
        cluster_directory_valid = self.app.cluster_entry.validate_text()

        if game_directory_valid and cluster_directory_valid:
            launch_data = self.app.launch_data_save_loader.load()

            if launch_data is None:
                if self.shard_frame.is_master:
                    launch_data = retrieve_launch_data(self.app.cluster_entry.get(), self.app.launch_data_save_loader)

                    if launch_data is None:
                        self.app.launch_data_popup.create(STRINGS.ERROR.LAUNCH_DATA_INVALID)

                        return
                else:
                    return

            logger.info(f"Starting {self.shard} shard...")

            self.shard_frame.set_starting()

            args, cwd = self.get_arguments(launch_data)

            #logger.debug("Starting server with these arguments: %s", " ".join(args))

            # This is HORRIBLE, but it works (Pyinstaller --noconcole + subprocess issue)
            with StdoutMock() as sys.stdout:
                self.process = popen_spawn.PopenSpawn(args, cwd=cwd, encoding="utf-8", codec_errors="ignore")

            self.task = PeriodicTask(self.app, random.randrange(50, 70), self.handle_output, initial_time=0)

    def execute_command(self, command, log=True):
        if not self.is_running():
            return

        if log:
            logger.info(f"({self.shard}) Executing console command: {command}")

        try:
            self.process.sendline(command)

        except OSError as e:
            logger.error(f"OSError during DedicatedServerShard [{self.shard}] execute_command function! Command: '{command}'. Actual error: '{e}'")

    def on_stopped(self):
        logger.info(f"{self.shard} shard is down...")

        if self.task:
            self.task.kill()

        self.shard_frame.set_offline()

        self.process = None
        self.task = None

    def stop(self):
        if not self.is_running():
            return

        if self.shard_frame.is_starting() or self.shard_frame.is_restarting():
            try:
                if psutil.pid_exists(self.process.pid):
                    psutil.Process(self.process.pid).terminate()

            except psutil.NoSuchProcess:
                logger.warning(f"NoSuchProcess exception while stopping {self.shard} shard.")

            self.on_stopped()
            self.app.stop_shards()

        elif self.shard_frame.is_online():
            self.shard_frame.set_stopping()

            self.execute_command(ANNOUNCE_STR.format(msg=STRINGS.COMMAND_ANNOUNCEMENT.SAVE_QUIT), log=False)
            self.execute_command(f"c_shutdown()")

            logger.info(f"Stopping {self.shard} shard...")

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

        self.handle_output_keywords(text=text)

        if self.shard_frame.is_master:
            vox_data = read_vox_data(self.app.master_shard, text)

            if vox_data:
                self.app.cluster_stats.update(vox_data)

        return True, None

    def handle_output_keywords(self, text):
        if "[Shard] Stopping" in text:
            logger.info(f"{self.shard_frame.code} was shut down... Stopping other shards.")

            self.shard_frame.set_stopping()
            self.app.stop_shards()

        elif "E_INVALID_TOKEN" in text or "E_EXPIRED_TOKEN" in text:
            logger.error("Invalid Token: E_INVALID_TOKEN or E_EXPIRED_TOKEN")

            self.app.token_entry.toggle_warning(False)
            self.app.stop_shards()

            self.app.error_popup.create(STRINGS.ERROR.TOKEN_INVALID)

        elif "Received world rollback request" in text:
            logger.info(f"{self.shard} received a rollback request...")

            self.app.shard_group.set_all_shards_restarting()

        elif "uploads added to server." in text:
            logger.info(f"{self.shard} is now online!")

            self.shard_frame.set_online()

            self.app.token_entry.toggle_warning(True)

        elif "SOCKET_PORT_ALREADY_IN_USE" in text:
            logger.error("Invalid cluster path or ports in use: SOCKET_PORT_ALREADY_IN_USE.")

            self.app.stop_shards()

            cluster_directory = Path(self.app.cluster_entry.get())
            config_file =  cluster_directory
            
            ports = []

            for shard in get_shard_names(cluster_directory):
                config_file = cluster_directory / shard / "server.ini"

                if config_file.exists():
                    port = get_key_from_ini_file(config_file, "server_port")
                    ports.append(f"{port} ({STRINGS.SHARD_NAME[shard.upper()] or shard})")

            self.app.error_popup.create(STRINGS.ERROR.PORTS.format(ports=", ".join(ports)))

        elif "[Error] Server failed to start!" in text:
            logger.error(f"{self.shard_frame.code} failed to start!")

            self.app.stop_shards()

            self.app.error_popup.create(STRINGS.ERROR.GENERAL)

        elif self.shard_frame.is_master and "Sim paused" in text:
            self.execute_command(load_lua_file("onserverpaused"), log=False)

        elif "LUA ERROR stack traceback" in text:
            logger.warning(f"{self.shard_frame.code} shard has crashed!")

            self.app.error_popup.create(STRINGS.ERROR.SERVER_CRASH)