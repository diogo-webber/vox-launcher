from pathlib import Path
import json, logging
from enum import Enum
from helpers import resource_path
from strings import get_default_language_code
from constants import LOGGER

logger = logging.getLogger(LOGGER)

class Settings(Enum):
    LANGUAGE = get_default_language_code()
    LAUNCH_OPTIONS = ""
    DISCORD_WEBHOOK = ""  # Discord webhook URL for logging
    DISCORD_GAME_LOGS_ONLY = False  # Only send game-related logs to Discord

class SettingsManager:
    """
    Class that manages the app's settings.

    Args:
        app (Ctk): the app instance.
        enum_cls (Enum): Enum class containing the settings and their defaults.
    """

    def __init__(self, enum_cls, app) -> None:
        self.app = app
        self.enum_cls = enum_cls
        self.settings = {}
        self._after_ids = {}  # Store after job IDs per setting key.
        self.file: Path = resource_path("savedata/settings.json").resolve()

        # Automatically add settings from enum.
        self.add_settings(enum_cls)

    def add_setting(self, key_enum, defaultvalue):
        """ Adds a new setting with a default value. """

        assert isinstance(key_enum, Enum), f"Setting key '{key_enum}' must be an Enum member."

        self.settings[key_enum] = {
            "value": None,
            "default": defaultvalue,
        }

    def add_settings(self, enum_cls):
        """ Adds multiple settings from Enum. """

        assert issubclass(enum_cls, Enum), "add_settings expects an Enum class."

        for key_enum in enum_cls:
            self.add_setting(key_enum, key_enum.value)

    def set_setting(self, key_enum, value):
        """ Sets a setting's value, saving only if it's not default. """

        setting = self.settings.get(key_enum)

        if not setting:
            return False

        # Skip if no change.
        if value == setting["value"]:
            return False

        # If reverting to default.
        if value == setting["default"]:
            if setting["value"] is not None:
                setting["value"] = None
                self.save()

                return True

            return False

        # Otherwise, save.
        setting["value"] = value
        self.save()

        return True

    def set_setting_delayed(self, key_enum, value, delay=2000):
        """ Debounced save: delays saving by 2s after last change. """

        # Cancel previous after job if exists.
        if key_enum in self._after_ids:
            self.app.after_cancel(self._after_ids[key_enum])

        def delayed_save():
            self.set_setting(key_enum, value)

            del self._after_ids[key_enum]

        # Schedule after.
        self._after_ids[key_enum] = self.app.after(delay, delayed_save)

        return True

    def save(self):
        """ Saves non-default settings to file. """

        settings_to_save = {
            key.name: setting["value"]
            for key, setting in self.settings.items()
            if setting["value"] is not None
        }

        self.file.parent.mkdir(exist_ok=True, parents=True)

        self.file.write_text(
            json.dumps(settings_to_save, sort_keys=True, indent=4, ensure_ascii=False),
            encoding="utf-8",
            errors="backslashreplace"
        )

    def load(self):
        """ Loads settings and updates values. """

        if not self.file.exists():
            return False

        try:
            data = json.loads(self.file.read_text(encoding="utf-8", errors="backslashreplace"))

        except json.JSONDecodeError:
            logger.warning(f"Corrupted settings file {self.file}. Creating backup.")

            self.file.replace(self.file.with_suffix(".corrupt.json"))

            return False

        for key_name, value in data.items():
            try:
                key_enum = self.enum_cls[key_name]

                if key_enum in self.settings:
                    self.settings[key_enum]["value"] = value
    
            except KeyError:
                logger.warning(f"Ignoring unknown setting: {key_name}")

        return True

    def get_setting(self, key_enum):
        """ Returns effective value for a setting. """

        setting = self.settings.get(key_enum)

        if not setting:
            return None

        return setting["value"] if setting["value"] is not None else setting["default"]

    def get_settings(self):
        """ Returns all settings as {key_enum: value} dict. """

        return {key_enum: self.get_setting(key_enum) for key_enum in self.settings}
