import os
import yaml
import sys
import ctypes

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

# Paths
LOCALIZATION_DIR = "app/localization"
BASE_FILE = "en_US.yaml"
BASE_PATH = os.path.join(LOCALIZATION_DIR, BASE_FILE)

IGNORED_KEYS = [
    "LANGUAGES"
]

def read_yaml(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}

def compare_keys(base_dict, target_dict, prefix=""):
    missing = []

    for key, value in base_dict.items():
        full_key = prefix and f"{prefix}.{key}" or key

        if key not in target_dict and not key in IGNORED_KEYS:
            missing.append(full_key)

        elif isinstance(value, dict) and isinstance(target_dict.get(key), dict):
            missing.extend(compare_keys(value, target_dict[key], full_key))

    return missing

def main(batch_mode: bool) -> bool:
    """Checks localization files for missing keys compared to the base file.

    Args:
        batch_mode (bool): Whether to format output for batch mode.

    Returns:
        bool: True if any file has missing keys, False otherwise.
    """

    base_data = read_yaml(BASE_PATH)
    failed = False
    prefix = "   " if batch_mode else "\n"

    for filename in os.listdir(LOCALIZATION_DIR):
        if not filename.endswith(".yaml") or filename == BASE_FILE:
            continue

        target_path = os.path.join(LOCALIZATION_DIR, filename)
        target_data = read_yaml(target_path)
        missing_keys = compare_keys(base_data, target_data)

        if missing_keys:
            if not failed and batch_mode:
                print()  # Extra space for batch readability

            failed = True
            print(f"{prefix}> {RED}Missing keys in {filename}:{RESET}")
            for key in missing_keys:
                print(f"{prefix}  - {key}")

        elif not batch_mode:
            print(f"{prefix}> {GREEN}No missing keys in {filename}{RESET}")

    return failed


if __name__ == "__main__":
    batch_mode = '--batch' in sys.argv
    exit_code = 1 if main(batch_mode) else 0
    sys.exit(exit_code)

