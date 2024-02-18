import os, shutil
from pathlib import Path

import PyInstaller.__main__ as PyInstaller

from app.constants import APP_VERSION

# ------------------------------------------------------------------------------ #

YELLOW = "\u001b[1m\u001b[38;5;214m"
GREEN  = "\u001b[1m\u001b[38;5;64m"
RESET  = "\u001b[0m"
NEW_LINE = "\n"

def print_header(title, color):
    TERMINAL_X = os.get_terminal_size().columns
    PRETTY_LINE = "-" * TERMINAL_X
    RESET_LINE = PRETTY_LINE + NEW_LINE + RESET

    print(f"{NEW_LINE}{color}{PRETTY_LINE}{NEW_LINE}{title.center(TERMINAL_X)}{NEW_LINE}{RESET_LINE}")

# ------------------------------------------------------------------------------ #

# Note: Local assets paths and app icon path are relative to WORK_DIRECTORY.

ASSETS_DIRECTORY = "../app/assets"
ASSETS_TEMP_DIRECTORY = "assets"

LUA_DIRECTORY = "../app/lua"
LUA_TEMP_DIRECTORY = "lua"

LOGGING_CONFIG_FILE = "../app/logging_config.yaml"
LOGGING_CONFIG_TEMP_FILE = "."

STRINGS_DIRECTORY = "../app/localization"
STRINGS_DIRECTORY_FILE = "localization"

WORK_DIRECTORY = "builddata"
BUILD_DIRECTORY = "builds"

DATA_DIRECTORY = "appdata"

FILE = "app/main.py"

EXE_NAME   = f"Vox Launcher"
BUILD_NAME = APP_VERSION
ZIP_NAME   = f"VoxLauncher.zip"

ICON = "../app/assets/icon.ico"

ONE_FILE = False
NO_CONSOLE = True

# ------------------------------------------------------------------------------ #

command_args = [
    f"--add-data={LOGGING_CONFIG_FILE};{LOGGING_CONFIG_TEMP_FILE}",

    f"--add-data={STRINGS_DIRECTORY};{STRINGS_DIRECTORY_FILE}",
    f"--add-data={ASSETS_DIRECTORY};{ASSETS_TEMP_DIRECTORY}",
    f"--add-data={LUA_DIRECTORY};{LUA_TEMP_DIRECTORY}",

    ONE_FILE and "--onefile" or f"--contents-directory={DATA_DIRECTORY}",
    NO_CONSOLE and "--noconsole" or "",
    "--noconfirm",
    "--clean",

    f"--name={EXE_NAME}",
    f"--icon={ICON}",
    f"--distpath={BUILD_DIRECTORY}",
    f"--workpath={WORK_DIRECTORY}",
    f"--specpath={WORK_DIRECTORY}",

    FILE,
]

# ------------------------------------------------------------------------------ #

if __name__ == "__main__":
    print_header(f"Building: {EXE_NAME}", color=YELLOW)

    PyInstaller.run(command_args)

    build_path = Path(BUILD_DIRECTORY) / EXE_NAME
    zip_temp_path = Path(WORK_DIRECTORY) / ("temp" + ".zip")
    zip_path = build_path / ZIP_NAME

    if build_path.exists():
        print(f"\nZipping file: {YELLOW}{ZIP_NAME}{RESET}...")

        # Created a zip file.
        shutil.make_archive(f"{WORK_DIRECTORY}/temp", 'zip', build_path)

        # Rename and move the zip file to "zip_path".
        zip_temp_path.rename(zip_path)

        new_build_path = build_path.with_name(BUILD_NAME)

        if new_build_path.exists():
            shutil.rmtree(new_build_path)

        # Rename the build folder to "new_build_path".
        build_path.rename(new_build_path)

    # Opens the directory in windows explorer.
    os.startfile(new_build_path)

    print_header("- Build Finished -", color=GREEN)
