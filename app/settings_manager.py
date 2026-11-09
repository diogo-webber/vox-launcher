from pathlib import Path
import json, logging
from helpers import resource_path
from strings import get_default_language_code
from constants import LOGGER

logger = logging.getLogger(LOGGER)

class Settings:
    """ Setting keys and their defaults. """

    LANGUAGE = "LANGUAGE"
    LAUNCH_OPTIONS = "LAUNCH_OPTIONS"

    # Set when an update is downloaded in-app, so the next launch shows the patch notes.
    SHOW_PATCH_NOTES = "SHOW_PATCH_NOTES"

    DEFAULTS = {
        LANGUAGE: get_default_language_code(),
        LAUNCH_OPTIONS: "",
        SHOW_PATCH_NOTES: False,
    }

class SettingsManager:
    """ Manages app settings, persisting only non-default values to disk. """

    def __init__(self, app) -> None:
        self.app = app
        self.defaults = Settings.DEFAULTS.copy()
        self.values = {}
        self._after_ids = {}
        self._pending = {}
        self.file: Path = resource_path("savedata/settings.json").resolve()

    def get(self, key):
        """ Returns the current value for a setting, or its default. """
        # A debounced value is already the user's choice, even if not saved yet.
        if key in self._pending:
            return self._pending[key]

        return self.values.get(key, self.defaults.get(key))

    def set(self, key, value):
        """ Sets a value, saving only if changed and non-default. """
        current = self.values.get(key, self.defaults.get(key))

        if value == current:
            return False

        if value == self.defaults.get(key):
            if key in self.values:
                del self.values[key]
                self.save()
                return True
            return False

        self.values[key] = value
        self.save()
        return True

    def set_delayed(self, key, value, delay=2000):
        """ Debounced set: waits for inactivity before saving. """
        if key in self._after_ids:
            self.app.after_cancel(self._after_ids[key])

        def delayed_save():
            self.set(key, self._pending.pop(key))
            del self._after_ids[key]

        self._pending[key] = value
        self._after_ids[key] = self.app.after(delay, delayed_save)
        return True

    def flush(self):
        """ Applies every pending delayed value right away. """
        for key, after_id in list(self._after_ids.items()):
            self.app.after_cancel(after_id)

            del self._after_ids[key]

            self.set(key, self._pending.pop(key))

    def save(self):
        """ Writes current non-default values to disk. """
        self.file.parent.mkdir(exist_ok=True, parents=True)
        self.file.write_text(
            json.dumps(self.values, sort_keys=True, indent=4, ensure_ascii=False),
            encoding="utf-8",
            errors="backslashreplace",
        )

    def load(self):
        """ Loads saved values from disk. """
        if not self.file.exists():
            return False

        try:
            data = json.loads(self.file.read_text(encoding="utf-8", errors="backslashreplace"))
        except OSError as e:
            logger.warning(f"Failed to read the settings file '{self.file}', falling back to the defaults: {e}")
            return False
        except json.JSONDecodeError:
            data = None

        if not isinstance(data, dict):
            logger.warning(f"The settings file '{self.file}' is corrupted, backing it up and falling back to the defaults.")
            self.file.replace(self.file.with_suffix(".corrupt.json"))
            return False

        for key, value in data.items():
            if key in self.defaults:
                self.values[key] = value
            else:
                logger.warning(f"Ignoring the unknown setting '{key}' found in '{self.file.name}'.")

        return True
