import yaml

from helpers import resource_path, get_system_language_code, DotDict
from constants import APP_VERSION

# ----------------------------------------------------------------------------------------- #

class DefaultDict(dict):
    def __missing__(self, key):
        return f"{{{key}}}"   # {key}

# ----------------------------------------------------------------------------------------- #

sys_lang_code = get_system_language_code()

sys_lang_filename = sys_lang_code + ".yaml"
default_sys_lang_filename = "en_US.yaml"

loc_dir = resource_path("localization")

loc_file = loc_dir / sys_lang_filename

loc_file = loc_file.exists() and loc_file or loc_dir / default_sys_lang_filename

strings = yaml.safe_load(loc_file.read_text(encoding="utf-8"))

STRINGS = DotDict(strings)

format_lookup = DefaultDict(
    APP_VERSION   = APP_VERSION,
    APP_NAME      = STRINGS.APP_NAME,
    GAME_TITLE    = STRINGS.ENTRY.GAME_TITLE,
    CLUSTER_TITLE = STRINGS.ENTRY.CLUSTER_TITLE,
    TOKEN_TITLE   = STRINGS.ENTRY.TOKEN_TITLE,
    LAUNCH        = STRINGS.LAUNCH_BUTTON.LAUNCH,
)

# ----------------------------------------------------------------------------------------- #

STRINGS.format_strings(format_lookup)
