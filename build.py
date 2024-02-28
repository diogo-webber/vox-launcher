import os, shutil
from pathlib import Path

import PyInstaller.__main__ as PyInstaller
import pyinstaller_versionfile

from app.constants import APP_VERSION

# ------------------------------------------------------------------------------ #

COLOR_TERM = os.getenv("COLORTERM")
TERMINAL_SUPPORT_COLORS = COLOR_TERM is not None and COLOR_TERM.lower() in ('truecolor', '256color')

YELLOW = TERMINAL_SUPPORT_COLORS and "\u001b[1m\u001b[38;5;214m" or ""
GREEN  = TERMINAL_SUPPORT_COLORS and "\u001b[1m\u001b[38;5;64m" or ""
RESET  = TERMINAL_SUPPORT_COLORS and "\u001b[0m" or ""
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

EXE_NAME   = "Vox Launcher"
BUILD_NAME = APP_VERSION
ZIP_NAME   = "VoxLauncher.zip"

ICON = "../app/assets/icon.ico"

VERSION_FILE_CREATE = "versionfile.txt"
VERSION_FILE = "../" + VERSION_FILE_CREATE

ONE_FILE = False
NO_CONSOLE = True

LOG_LEVEL = "WARN"

# ------------------------------------------------------------------------------ #

pyinstaller_versionfile.create_versionfile(
    output_file=VERSION_FILE_CREATE,
    version=APP_VERSION[1:],
    file_description=EXE_NAME, # It's also the Task Bar "group" name.
    internal_name=EXE_NAME,
    legal_copyright="Open Source @ 2024",
    product_name=EXE_NAME,
    translations=[0x0409, 1200],
)

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
    f"--version-file={VERSION_FILE}",
    f"--log-level={LOG_LEVEL}",

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
