import os, shutil, sys, ctypes, time
from pathlib import Path
from datetime import datetime

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

import PyInstaller.__main__ as PyInstaller
import pyinstaller_versionfile

from app.constants import APP_VERSION

RENAME_ATTEMPTS = 3

# ------------------------------------------------------------------------------ #

# Enable colors for cmd.
kernel32 = ctypes.windll.kernel32
handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE = -11
mode = ctypes.c_ulong()
kernel32.GetConsoleMode(handle, ctypes.byref(mode))
kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING

COLOR_TERM = os.getenv("COLORTERM")
TERMINAL_SUPPORT_COLORS = COLOR_TERM is not None and COLOR_TERM.lower() in ('truecolor', '256color')

# Colors
ESC = "\033"
RESET = f"{ESC}[0m"

if TERMINAL_SUPPORT_COLORS:
    # Rich colors.
    YELLOW = f"{ESC}[1m{ESC}[38;5;214m"
    GREEN  = f"{ESC}[1m{ESC}[38;5;64m"
    RED    = f"{ESC}[1m{ESC}[38;5;196m"
else:
    # Basic ANSI fallback.
    YELLOW = f"{ESC}[33m"
    GREEN  = f"{ESC}[32m"
    RED    = f"{ESC}[31m"

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

VERSION_FILE_CREATE = WORK_DIRECTORY + "/versionfile.txt"
VERSION_FILE = "versionfile.txt" # Relative to WORK_DIRECTORY

ONE_FILE = False
NO_CONSOLE = True

LOG_LEVEL = "WARN"

# ------------------------------------------------------------------------------ #

pyinstaller_versionfile.create_versionfile(
    output_file=VERSION_FILE_CREATE,
    version=APP_VERSION[1:],
    file_description=EXE_NAME, # It's also the Task Bar "group" name.
    internal_name=EXE_NAME,
    legal_copyright=f"Open Source @ {datetime.now().year}",
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

    # Exclude problematic imports
    "--exclude-module=AppKit",
    "--exclude-module=_mac_detect",

    # Handle DLL warnings
    f"--runtime-hook={Path(__file__).parent / 'fix_dll_imports.py'}",

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

def wait_for_file_access(path, timeout=5):
    """Wait for file to be accessible"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with open(path, 'a'):
                return True
        except PermissionError:
            time.sleep(0.1)
    return False

def rename_build_folder(old, new):
    for attempt in range(RENAME_ATTEMPTS):
        try:
            if attempt > 0:
                print(f"{YELLOW}[INFO]{RESET} Renaming build folder to: {YELLOW}{new.as_posix()}{RESET} [Attempt {attempt+1}]")
            else:
                print(f"{YELLOW}[INFO]{RESET} Renaming build folder to: {YELLOW}{new.as_posix()}{RESET}")

            # Wait for files to be released
            for file in old.rglob('*'):
                if file.is_file():
                    wait_for_file_access(file)
            
            # Try to rename
            old.rename(versioned_build_path)
            break

        except Exception as e:
            if attempt + 1 < RENAME_ATTEMPTS:
                print(f"{RED}[ERROR]{RESET} Failed to rename build folder, files might be in use. Retrying in {YELLOW}100{RESET} milliseconds...")
                time.sleep(0.1)
            else:
                print(f"{RED}[ERROR]{RESET} Failed to rename build folder, files might be in use.")
                raise e  # Give up after last attempt.

if __name__ == "__main__":
    print_header(f"Building: {EXE_NAME}", color=YELLOW)

    # Run PyInstaller
    PyInstaller.run(command_args)

    # Define paths
    build_path = Path(BUILD_DIRECTORY) / EXE_NAME
    zip_temp_path = Path(WORK_DIRECTORY) / "temp.zip"
    zip_path = build_path / ZIP_NAME
    versioned_build_path = Path(BUILD_DIRECTORY) / BUILD_NAME

    print() # For spacing.

    # Ensure build folder exists
    if not build_path.exists():
        print(f"{RED}[ERROR]{RESET} Build output folder not found: {RED}{build_path.as_posix()}{RED}")
        sys.exit(1)

    # Clean up old versioned folder if exists
    if versioned_build_path.exists():
        print(f"{YELLOW}[INFO]{RESET} Removing old versioned build folder: {YELLOW}{versioned_build_path.as_posix()}{RESET}")
        shutil.rmtree(versioned_build_path)

    # Rename build folder
    rename_build_folder(build_path, versioned_build_path)

    # Zip the build folder
    print(f"{YELLOW}[INFO]{RESET} Zipping build folder as: {YELLOW}{ZIP_NAME}{RESET}")
    shutil.make_archive(str(zip_temp_path.with_suffix('')), 'zip', versioned_build_path)

    # Move zip to build folder
    final_zip_path = versioned_build_path / ZIP_NAME
    zip_temp_path.rename(final_zip_path)

    print(f"{GREEN}[SUCCESS]{RESET} Build zipped at: {GREEN}{final_zip_path.as_posix()}{RESET}")

    # Open folder in Explorer
    os.startfile(versioned_build_path)

    print_header("- Build Finished -", color=GREEN)

    sys.exit(0)

