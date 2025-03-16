import os
import yaml

# Check if terminal supports colors
COLOR_TERM = os.getenv("COLORTERM")
TERMINAL_SUPPORT_COLORS = COLOR_TERM is not None and COLOR_TERM.lower() in ('truecolor', '256color')

# Define color codes conditionally
GREEN  = TERMINAL_SUPPORT_COLORS and "\u001b[1m\u001b[38;5;64m" or ""
RED    = TERMINAL_SUPPORT_COLORS and "\u001b[1m\u001b[38;5;196m" or ""
RESET  = TERMINAL_SUPPORT_COLORS and "\u001b[0m" or ""

# Paths
LOCALIZATION_DIR = "app/localization"
BASE_FILE = "en_US.yaml"
BASE_PATH = os.path.join(LOCALIZATION_DIR, BASE_FILE)

def read_yaml(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}

def compare_keys(base_dict, target_dict, prefix=""):
    missing = []

    for key, value in base_dict.items():
        full_key = prefix and f"{prefix}.{key}" or key

        if key not in target_dict:
            missing.append(full_key)

        elif isinstance(value, dict) and isinstance(target_dict.get(key), dict):
            missing.extend(compare_keys(value, target_dict[key], full_key))

    return missing

def main():
    base_data = read_yaml(BASE_PATH)

    for filename in os.listdir(LOCALIZATION_DIR):
        if filename.endswith(".yaml") and filename != BASE_FILE:
            target_path = os.path.join(LOCALIZATION_DIR, filename)
            target_data = read_yaml(target_path)

            missing_keys = compare_keys(base_data, target_data)

            if missing_keys:
                print(f"\n{RED}Missing keys in {filename}:{RESET}")
                for key in missing_keys:
                    print(f"  - {key}")
            else:
                print(f"\n{GREEN}No missing keys in {filename}{RESET}")

if __name__ == "__main__":
    main()
