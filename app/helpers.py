from pathlib import Path
import winreg, ctypes
from dataclasses import dataclass
import ctypes.wintypes
import webbrowser
import re, json, sys
import logging, locale
from pexpect.exceptions import TIMEOUT, EOF

from constants import LOGGER

logger = logging.getLogger(LOGGER)

# ----------------------------------------------------------------------------------------- #

def resource_path(relative_path: str) -> Path:
    """ Get absolute path to resource, works for dev and for PyInstaller """

    base_path = Path(getattr(sys, '_MEIPASS', Path(sys.argv[0]).absolute().parent))

    return base_path / relative_path

# ----------------------------------------------------------------------------------------- #

@dataclass
class TextHightlightData():
    """
    Simple dataclass used to highlight text in text box widgets.

    Args:
        name (str): the indentifier.
        pattern (re.Pattern): Matched text using this pattern will be highlighted.
    """
    name: str
    pattern: re.Pattern

# ----------------------------------------------------------------------------------------- #

class DotDict:
    """
    Cast a dict into an object with dot notation.

    Args:
        dictionary (dict): the dict to be casted.
    """

    def __init__(self, dictionary):
        for key, value in dictionary.items():
            if isinstance(value, dict):
                setattr(self, key, DotDict(value))
            else:
                setattr(self, key, value)

    def __repr__(self):
        return json.dumps(
            self.to_dict(),
            indent = 4,
            ensure_ascii = False
        )

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        return setattr(self, key, value)

    def format_strings(self, format_lookup):
        """
        Format every string with the key-value pairs of format_lookup.

        Args:
            format_lookup (DefaultDict): the dict containing the format data.
        """

        for key, value in self.__dict__.items():
            if isinstance(value, DotDict):
                value.format_strings(format_lookup)

            elif isinstance(value, str):
                self.__dict__[key] = value.format_map(format_lookup)

            elif isinstance(value, list):
                for i, item in enumerate(value):
                    self.__dict__[key][i] = item.format_map(format_lookup)

    def to_dict(self):
        """
        Cast self into the built-in dict type.

        Returns:
            dict (dict): the dict contaning the data of self.
        """
        result = {}

        for key, value in self.__dict__.items():
            if isinstance(value, DotDict):
                result[key] = value.to_dict()
            else:
                result[key] = value

        return result


# ----------------------------------------------------------------------------------------- #

def resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller.

    Args:
        relative_path (str): the relative path to resource.
    """

    base_path = Path(getattr(sys, '_MEIPASS', Path(__file__).absolute().parent))

    return base_path / relative_path

# ----------------------------------------------------------------------------------------- #

class SaveLoader:
    """
    Class that manages save-load cycle.

    Args:
        filename (str): filename, with suffix.
    """

    def __init__(self, filename):
        self.file: Path = resource_path(f"savedata/{filename}")

    def save(self, /, **kwargs):
        """ Saves kwargs to self.file. """

        self.file.parent.mkdir(exist_ok=True, parents=True)

        self.file.write_text(
            json.dumps(
                kwargs,
                sort_keys = True,
                indent = 4,
                ensure_ascii = False
            ),
            encoding="utf-8"
        )

    def load(self):
        """
        Loads self.file and returns the data loaded.

        Returns:
            None if the file doesn't exists, otherwise a DotDict instance containing the data loaded.
        """

        if not self.file.exists():
            return

        data = json.loads(self.file.read_text(encoding="utf-8"))

        return DotDict(data)


# ----------------------------------------------------------------------------------------- #

class PeriodicTask():
    """
    Executes a function in a loop.

    Args:
        app (CTk): window root widget.
        time (int, float): interval in milliseconds to execute the function.
        initial_time (int, float): override "time" argument in the first call. Optional.
        func (function): the function to called every "time" milliseconds.
        This function needs to return 2 values:
            success (bool, None): if not True, stops the loop.
            newtime: (int, float, None): override "time" for the next call, if not None. Optional.
        args (list): additional parameters to give as parameters to the function call.
    """
    def __init__(self, app, time, initial_time, func, *args) -> None:
        self.app = app
        self.time = time
        self.func = func
        self.args = args

        self.id = self.app.after(initial_time or time, self._execute, *self.args)

    def _execute(self, *args):
        success, newtime = self.func(*args)

        self.id = None

        if success:
            self.id = self.app.after(newtime or self.time, self._execute, *self.args)

    def kill(self):
        """ Stops the loop. """

        if self.id:
            logger.debug(f"Killing periodic task <{self.id}>")
            self.app.after_cancel(self.id)

# ----------------------------------------------------------------------------------------- #

def read_vox_data(server, text):
    """
    Searches "text" trying to find Vox Launcher data.

    Args:
        server (DedicatedServerShard): shard that is out putting text.
        text (str): text that will be searched for data.

    Returns:
        Dict containing the data read or None.
    """

    pattern = re.compile(r'VoxLauncherData=({.+})')
    matches = pattern.findall(text)

    if not matches:
        return

    if len(matches) > 1:
        # Data overload! Grab new data.
        server.execute_command("VoxLauncher_GetServerStats()")

    else:
        string = matches[0].strip()

        return json.loads(string)

def handle_shard_output(shard):
    """
    Reads all new data from shard.process and handle key phases.
    Should be used in a PeriodicTask.

    Args:
        shard (DedicatedServerShard): shard to read from.

    Returns:
        success (bool, None): if not True, stops the loop. See PeriodicTask._execute.
        newtime: (int, float, None): override PeriodicTask.time for the next call, if not None. See PeriodicTask._execute.
    """

    if not shard.is_running():
        shard.on_stopped()
        shard.app.stop_shards()

        return False, None

    text = None

    try:
        text = shard.process.read_nonblocking(size=9999, timeout=None)

    except (EOF, TIMEOUT):
        return True, 500

    if not text:
        return True, None

    shard.shard_frame.shard_log_panel.append_text(text)

    if shard.shard_frame.is_master:
        vox_data = read_vox_data(shard.app.master_shard, text)

        if vox_data:
            shard.app.cluster_stats.update(vox_data)

    if "World generated on build" in text:
        logger.info(f"{shard.shard_frame.code} is now online!")

        shard.shard_frame.set_online()

        shard.app.token_entry.toggle_warning(True)

    elif "Received world rollback request" in text:
        shard.app.shard_group.set_all_shards_restarting()

    elif "E_INVALID_TOKEN" in text or "E_EXPIRED_TOKEN" in text:
        logger.error("Invalid Token: E_INVALID_TOKEN or E_EXPIRED_TOKEN")

        shard.app.token_entry.toggle_warning(False)
        shard.app.stop_shards()

    elif "SOCKET_PORT_ALREADY_IN_USE" in text:
        logger.error("Invalid cluster path or ports in use: SOCKET_PORT_ALREADY_IN_USE")

        shard.app.stop_shards()

    elif "[Error] Server failed to start!" in text:
        logger.error(f"{shard.shard_frame.code} failed to start!")

        shard.app.stop_shards()

    # Runs mainly on master.
    elif "]: Shutting down" in text:
        logger.info(f"{shard.shard_frame.code} was shut down... Stopping")

        shard.app.stop_shards()

    return True, None

# ----------------------------------------------------------------------------------------- #

def get_key_from_ini_file(file, key):
    """
    Reads an .ini file and returns the key's value.

    Args:
        file (Path): the Path object.
        key (str): key to look for.

    Returns:
        value (str, None): the key's value or None.
    """

    pattern = re.compile(rf'{key}\s*=\s*(.+)')

    text  = file.read_text(encoding="utf-8")
    match = pattern.search(text)

    if match:
        return match.group(1).strip()

DEFAULT_MAX_SNAPSHOTS = 6

def _get_max_rollbacks(cluster_settings):
    """
    Reads an .ini file and returns the max_snapshots value.

    Args:
        cluster_settings (Path): a .ini file.

    Returns:
        value (int): cluster_settings's max_snapshots or DEFAULT_MAX_SNAPSHOTS.
    """

    if cluster_settings.exists():
        max_snapshots = get_key_from_ini_file(cluster_settings, "max_snapshots")

        return max_snapshots or DEFAULT_MAX_SNAPSHOTS

    return DEFAULT_MAX_SNAPSHOTS

def rollback_slider_fn(app):
    """
    Rollback slider function. Used in PopUp.create.

    Args:
        app (Ctk): the app instance.

    Returns:
        min (int), max (int): slider's min and max value.
    """

    cluster_directory = Path(app.cluster_entry.get())

    return 1, _get_max_rollbacks(cluster_directory / "cluster.ini")

# ----------------------------------------------------------------------------------------- #

GAME_DIRECTORY_REQUIRED_CHILDREN = [ "bin64/dontstarve_dedicated_server_nullrenderer_x64.exe", "bin64/dontstarve_dedicated_server_r_x64.exe" ]
CLUSTER_DIRECTORY_REQUIRED_CHILDREN = [ "cluster.ini", "Master" ]


def validate_directory(directory, required_children, one_of=False) :
    """
    Checks if directory contains all required_children subpaths.

    Args:
        directory (Path, str): the directory path.
        required_children (list): the subpaths that directory must contain.
        one_of (bool): if True, just one required_children's subpath is required. Default: False.

    Returns:
        valid (bool): valid or not.
    """

    directory = Path(directory)

    if not directory.exists():
        logger.debug(f"Validate Directory: directory '{directory}' doesn't exist...")
        return False

    missing_children = list(filter(lambda child: not (directory / child).exists(), required_children))

    if (one_of and len(required_children) == len(missing_children)) or (not one_of and missing_children):
        logger.debug(f"Validate Directory: required children '{missing_children}' doesn't exist in '{directory}'...")
        return False

    return True

def validate_game_directory(directory: str) -> bool:
    return validate_directory(directory, GAME_DIRECTORY_REQUIRED_CHILDREN, one_of=True)

def validate_cluster_directory(directory: str) -> bool:
    return validate_directory(directory, CLUSTER_DIRECTORY_REQUIRED_CHILDREN)

# ----------------------------------------------------------------------------------------- #

def open_klei_account_page(*args, **kwargs):
    """ Opens Klei dedicated servers website in the default browser. """

    webbrowser.open("https://accounts.klei.com/account/game/servers?game=DontStarveTogether", new=0, autoraise=True)

# ----------------------------------------------------------------------------------------- #

def read_only_bind(event):
    """ Widget key binding that makes a text widget read-only, but allows copying ( CTRL + C ). """

    if event.state == 12 and event.keysym == "c":
        return

    return "break"

def disable_bind(event):
    return "break"

# ----------------------------------------------------------------------------------------- #

LUA_FOLDER = Path(__file__).absolute().parent / "lua"

def load_lua_file(filename):
    """
    Loads a .lua file and returns its content, joining its lines.

    Args:
        filename (str): the filename, without suffix. Must be inside lua/ folder.

    Returns:
        text (str, None): the text if the file exists, None otherwise.
    """

    file = LUA_FOLDER / (filename + ".lua")

    if file.exists():
        text = file.read_text(encoding="utf-8")

        # Remove single line comments.
        comment_pattern = re.compile(r'--.*?[\r\n]')
        text = re.sub(comment_pattern, '', text)

        return " ".join(text.split())

    else:
        logger.error("load_lua_file: File [%s] doesn't exist...", str(file))

# ----------------------------------------------------------------------------------------- #

FR_PRIVATE  = 0x10
FR_NOT_ENUM = 0x20

# This function was taken from
# https://github.com/ifwe/digsby/blob/f5fe00244744aa131e07f09348d10563f3d8fa99/digsby/src/gui/native/win/winfonts.py#L15
# and adapted to work in python 3

def loadfont(fontpath, private = True, enumerable = False):
    '''
    Makes fonts located in file "fontpath" available to the font system.

    private  if True, other processes cannot see this font, and this font
             will be unloaded when the process dies

    enumerable  if True, this font will appear when enumerating fonts

    see http://msdn2.microsoft.com/en-us/library/ms533937.aspx
    '''

    if isinstance(fontpath, bytes):
        pathbuf = ctypes.create_string_buffer(fontpath)
        AddFontResourceEx = ctypes.windll.gdi32.AddFontResourceExA
    elif isinstance(fontpath, str):
        pathbuf = ctypes.create_unicode_buffer(fontpath)
        AddFontResourceEx = ctypes.windll.gdi32.AddFontResourceExW
    else:
        raise TypeError('fontpath must be a bytes or str')

    flags = (FR_PRIVATE if private else 0) | (FR_NOT_ENUM if not enumerable else 0)

    numFontsAdded = AddFontResourceEx(ctypes.byref(pathbuf), flags, 0)

    return bool(numFontsAdded)

# ----------------------------------------------------------------------------------------- #

def get_system_language_code():
    windll = ctypes.windll.kernel32
    windll.GetUserDefaultUILanguage()

    return locale.windows_locale[ windll.GetUserDefaultUILanguage() ]

# ----------------------------------------------------------------------------------------- #


def sort_key(shardname):
    return dict(Master = 0, Caves = 1).get(shardname, 3)

def get_shard_names(cluster):
    """
    Collect all directory names inside a cluster folder that contain 'server.ini' (the shard names).

    Args:
        cluster (str, Path): the cluster path.

    Returns:
        A list of shard names (strings).
    """

    cluster = Path(cluster)
    shards = []

    for directory in cluster.iterdir():
        if directory.is_dir() and (directory / "server.ini").exists():
            shards.append(directory.stem)

    return sorted(shards, key=sort_key)

# ----------------------------------------------------------------------------------------- #

def get_cluster_relative_path(path):
    """
    Gets the cluster relative path to the Klei/DoNotStarveTogether or Klei/DoNotStarveTogetherBetaBranch.

    Args:
        path (Path): the cluster path.

    Returns:
        relative_path (str): the relative path or path.name.
    """

    regex = re.compile(r'Klei/DoNotStarveTogether(?:BetaBranch)?/(.*)')

    match = regex.search(path.as_posix())

    if match:
        return match.group(1)

    return path.name

# ----------------------------------------------------------------------------------------- #

def get_game_directory():
    """
    Attempts to determine the user's Don't Starve Together directory.

    Returns:
        directory (Path, None): the directory path or None.
    """

    try:
        # Open the Steam App 322330 registry key.
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Steam App 322330") as key:
            # Read the install location path from the registry
            game_path, _ = winreg.QueryValueEx(key, "InstallLocation")

            if validate_game_directory(game_path):
                return Path(game_path)

    except FileNotFoundError:
        logger.debug("FileNotFoundError exception when trying to get the Game directory using: [...]\\Steam App 322330 - InstallLocation.")

    try:
        # Open the Steam registry key.
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            # Read the Steam installation path from the registry
            steam_path, _ = winreg.QueryValueEx(key, "SteamPath")

            directory = Path(steam_path) / "steamapps/common/Don't Starve Together"

            if validate_game_directory(directory):
                return directory

    except FileNotFoundError:
        logger.debug("FileNotFoundError exception when trying to get the Game directory using: Software\\Valve\\Steam - SteamPath.")


CSIDL_PERSONAL = 5       # Documents
SHGFP_TYPE_CURRENT = 0   # Get current, not default value

def _get_documents_folder():
    """
    Determines the user's document directory.

    Returns:
        directory (Path, None): the documents directory path or None.
    """

    buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
    ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)

    return buf.value

def get_clusters_directory():
    """
    Attempts to determine the user's cluster persistent storage.

    Returns:
        directory (Path, None): the directory path or None.
    """

    dst_directory = Path(_get_documents_folder()) / "Klei/DoNotStarveTogether"

    if not dst_directory.exists():
        return None

    if (dst_directory / "client.ini").exists():
        return dst_directory

    # Some users have their clusters inside a numeric folder.
    for directory in dst_directory.iterdir():
        if directory.is_dir() and directory.name.isdigit() and (directory / "client.ini").exists():
            return directory

    return None
