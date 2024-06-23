import logging

import sys, os
import random
import logging, logging.config

from pathlib import Path
from io import TextIOWrapper

from pexpect import popen_spawn
from signal import SIGTERM

from constants import *
from helpers import *
from strings import STRINGS

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
    
    def get_arguments(self):
        game_directory    = Path(self.app.game_entry.get()   )
        cluster_directory = Path(self.app.cluster_entry.get())

        token = self.app.token_entry.get()
        cluster, user_dir, storage_root = get_cluster_and_user_dir_and_storage_root(cluster_directory)
        ugc_directory = get_ugc_directory()

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

        if user_dir is not None:
            args.append("-ownerdir")
            args.append(user_dir)
        else:
            logger.warning("Starting shard: missing user dir.")

        if storage_root is not None:
            args.append("-persistent_storage_root")
            args.append(storage_root.as_posix())
        else:
            logger.warning("Starting shard: missing storage root.")

        if ugc_directory is not None:
            args.append("-ugc_directory")
            args.append(ugc_directory.as_posix())
        else:
            logger.warning("Starting shard: missing mods directory.")

        return args, str(cwd)

    def start(self):
        if self.is_running():
            logger.warning(f"Shard {self.shard} is already running...")
            return

        game_directory_valid       = self.app.game_entry.validate_text()
        cluster_directory_valid    = self.app.cluster_entry.validate_text()

        if game_directory_valid and cluster_directory_valid:
            logger.info(f"Starting {self.shard} shard...")

            self.shard_frame.set_starting()

            args, cwd = self.get_arguments()

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
            self.process.kill(SIGTERM)
            self.on_stopped()
            self.app.stop_shards()

        elif self.shard_frame.is_online():
            self.shard_frame.set_stopping()

            self.execute_command(ANNOUNCE_STR.format(msg="Saving and closing!"), log=False)
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
        if "E_INVALID_TOKEN" in text or "E_EXPIRED_TOKEN" in text:
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

                if config_file.exists:
                    port = get_key_from_ini_file(config_file, "server_port")
                    ports.append(f"{port} ({shard})")

            self.app.error_popup.create(STRINGS.ERROR.PORTS.format(ports=", ".join(ports)))

        elif "[Error] Server failed to start!" in text:
            logger.error(f"{self.shard_frame.code} failed to start!")

            self.app.stop_shards()

            self.app.error_popup.create(STRINGS.ERROR.GENERAL)

        # Runs mainly on master.
        elif "]: Shutting down" in text:
            logger.info(f"{self.shard_frame.code} was shut down... Stopping other shards.")

            self.shard_frame.set_stopping()
            self.app.stop_shards()

        elif self.shard_frame.is_master and "Sim paused" in text:
            self.execute_command(load_lua_file("onserverpaused"), log=False)
