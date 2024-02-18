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

    def start(self):
        if self.is_running():
            logger.warning(f"Shard {self.shard} is already running...")
            return

        game_directory_valid       = self.app.game_entry.validate_text()
        cluster_directory_valid    = self.app.cluster_entry.validate_text()

        if game_directory_valid and cluster_directory_valid:
            game_directory    = Path(self.app.game_entry.get()   )
            cluster_directory = Path(self.app.cluster_entry.get())

            token = self.app.token_entry.get()
            cluster = get_cluster_relative_path(cluster_directory)

            cwd = (game_directory / "bin64").resolve()
            exe = (cwd / "dontstarve_dedicated_server_nullrenderer_x64").resolve()

            if not exe.with_suffix(".exe").exists():
                # Dev build executable
                exe = (cwd / "dontstarve_dedicated_server_r_x64").resolve()

            logger.info(f"Starting {self.shard} shard...")

            self.shard_frame.set_starting()

            args = f"{exe} -cluster {cluster} -shard {self.shard} -token {token} -monitor_parent_process {PROCESS_ID}"

            # This is HORRIBLE, but it works (Pyinstaller --noconcole + subprocess issue)
            with StdoutMock() as sys.stdout:
                self.process = popen_spawn.PopenSpawn(args, cwd=str(cwd), encoding="utf-8", codec_errors="ignore")

            self.task = PeriodicTask(self.app, random.randrange(50, 70), handle_shard_output, self, initial_time=0)

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
