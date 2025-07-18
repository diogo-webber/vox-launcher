import yaml, locale
import ctypes
import ctypes.wintypes
from helpers import resource_path, DotDict
from constants import APP_VERSION

DEBUG_LANG_CODE = None  # "zh_CN"

# ----------------------------------------------------------------------------------------- #

def get_system_language_code():
    """
    Retrieves the system UI language code on Windows.

    Returns:
        str: The language code in the format 'en_US', 'pt_BR', etc.
    """

    windll = ctypes.windll.kernel32
    lang_id = windll.GetUserDefaultUILanguage()

    return locale.windows_locale[lang_id]

def get_default_language_code():
    """
    Retrieves the system UI language code on Windows and returns a supported language code.

    Returns:
        str: A language code in the format 'en_US', 'pt_BR', etc.
    """

    code = get_system_language_code()

    return STRINGS.LANGUAGES[code] is not None and code or "en_US"

def get_readable_system_language():
    """
    Retrieves the system's language in a human-readable format.

    Returns:
        str: The name of the system language (e.g., 'English', 'Portuguese').
             Returns 'Unknown' if the language cannot be determined.
    """
    language, _ = locale.getlocale()

    if language:
        return language.split('_')[0]
    
    return "Unknown"

# ----------------------------------------------------------------------------------------- #

class DefaultDict(dict):
    def __missing__(self, key):
        return f"{{{key}}}"  # {key}

# ----------------------------------------------------------------------------------------- #

LOC_DIR = resource_path("localization")
FALLBACK_FILE = LOC_DIR / "en_US.yaml"

class Strings(DotDict):
    _instance = None  # Singleton instance.
    _lang_code = "en_US"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance

    def __init__(self):
        # Load fallback (English) strings initially
        fallback_strings = yaml.safe_load(FALLBACK_FILE.read_text(encoding="utf-8", errors="backslashreplace"))
        super().__init__(fallback_strings)

        # Format fallback
        self._format_strings()

    def load_strings(self, lang_code: str) -> None:
        lang_code = DEBUG_LANG_CODE or lang_code
        loc_file = LOC_DIR / f"{lang_code}.yaml"

        if loc_file.exists():
            loaded_strings = yaml.safe_load(loc_file.read_text(encoding="utf-8", errors="backslashreplace"))

            super().__init__(loaded_strings)

            self._lang_code = lang_code

            # Apply formatting
            self._format_strings()

    @property
    def current_language_code(self):
        return self._lang_code

    def _format_strings(self):
        format_lookup = DefaultDict(
            APP_VERSION=APP_VERSION,
            APP_NAME=self.APP_NAME,
            GAME_TITLE=self.ENTRY.GAME_TITLE,
            CLUSTER_TITLE=self.ENTRY.CLUSTER_TITLE,
            TOKEN_TITLE=self.ENTRY.TOKEN_TITLE,
            LAUNCH=self.LAUNCH_BUTTON.LAUNCH,
        )
        self.format_strings(format_lookup)

# Usage
STRINGS = Strings()