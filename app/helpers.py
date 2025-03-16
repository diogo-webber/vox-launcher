from pathlib import Path
import winreg, ctypes
from dataclasses import dataclass
import ctypes.wintypes
import webbrowser
import re, json, sys
import logging, locale
import psutil, os, zipfile

from constants import LOGGER

logger = logging.getLogger(LOGGER)

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
        initial_time (int, float, None): override "time" argument in the first call. Optional.
        func (function): the function to called every "time" milliseconds.
        This function needs to return 2 values:
            success (bool, None): if not True, stops the loop.
            newtime: (int, float, None): override "time" for the next call, if not None. Optional.
        args (list): additional parameters to give as parameters to the function call.
    """
    def __init__(self, app, time, func, *args, initial_time=None) -> None:
        self.app = app
        self.time = time
        self.func = func
        self.args = args

        self.id = self.app.after(initial_time or time, self._execute)

    def _execute(self, *args):
        success, newtime = self.func(*self.args)

        self.id = None

        if success:
            self.id = self.app.after(newtime or self.time, self._execute)

    def kill(self):
        """ Stops the loop. """

        if self.id:
            #logger.debug(f"Killing periodic task <{self.id}>")
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

GAME_DIRECTORY_ONE_OF_CHILDREN = [ "bin64/dontstarve_dedicated_server_nullrenderer_x64.exe", "bin64/dontstarve_dedicated_server_r_x64.exe" ]
CLUSTER_DIRECTORY_REQUIRED_CHILDREN = [ "cluster.ini", "Master" ]

def validate_directory(directory, required_children=None, one_of_children=None) :
    """
    Checks if directory contains all required_children subpaths and/or one_of_children subpaths.

    Args:
        directory (Path, str): the directory path.
        required_children (list, None): the subpaths that directory must contain.
        one_of_children (list, None): the subpaths that directory must contain at least one of.

    Returns:
        valid (bool): valid or not.
    """

    directory = Path(directory)

    if not directory.exists():
        logger.debug(f"Validate Directory: directory '{directory}' doesn't exist...")
        return False

    if required_children:
        for child in required_children:
            if not (directory / child).exists():
                logger.debug(f"Validate Directory: required child '{child}' doesn't exist in '{directory}'...")
                return False

    if one_of_children:
        missing_children = list(filter(lambda child: not (directory / child).exists(), one_of_children))

        if one_of_children == missing_children:
            logger.debug(f"Validate Directory: missing one of these {one_of_children} in '{directory}'...")
            return False

    return True

def validate_game_directory(directory: str) -> bool:
    return validate_directory(directory, one_of_children=GAME_DIRECTORY_ONE_OF_CHILDREN)

def validate_cluster_directory(directory: str) -> bool:
    return validate_directory(directory, required_children=CLUSTER_DIRECTORY_REQUIRED_CHILDREN)

# ----------------------------------------------------------------------------------------- #

def open_klei_account_page(*args, **kwargs):
    """ Opens Klei dedicated servers website in the default browser. """

    webbrowser.open("https://accounts.klei.com/account/game/servers?game=DontStarveTogether", new=0, autoraise=True)

def open_github_issue(*args, **kwargs):
    """ Opens Vox Launcher repository on Github, in the issues tab, in the default browser. """

    webbrowser.open("https://github.com/diogo-webber/vox-launcher/issues/new", new=0, autoraise=True)


def open_folder(path):
    """ Opens a Windows explorer instance on this path  """

    os.startfile(path)

def open_file(path):
    """ Opens a file  """

    os.startfile(path)

# ----------------------------------------------------------------------------------------- #

def disable_bind(event):
    return "break"

# ----------------------------------------------------------------------------------------- #

LUA_FOLDER = Path(__file__).absolute().parent / "lua"

lua_file_cache = {}

def load_lua_file(filename):
    """
    Loads a .lua file and returns its content, joining its lines.

    Args:
        filename (str): the filename, without suffix. Must be inside lua/ folder.

    Returns:
        text (str, None): the text if the file exists, None otherwise.
    """

    file = LUA_FOLDER / (filename + ".lua")

    if lua_file_cache.get(file.as_posix()):
        return lua_file_cache[file.as_posix()]

    if file.exists():
        text = file.read_text(encoding="utf-8")

        # Remove single line comments.
        comment_pattern = re.compile(r'--.*?[\r\n]')
        text = re.sub(comment_pattern, '', text)

        text = " ".join(text.split())

        lua_file_cache[file.as_posix()] = text

        return text

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
    """Master first, then Caves and then the others"""
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

def get_cluster_name(path):
    """
    Gets the cluster relative path.

    Args:
        path (Path): the cluster path.

    Returns:
        cluster (str): the cluster relative path.

    """

    regex = re.compile(r'/DoNotStarveTogether(?:BetaBranch)?/(.*)')

    match = regex.search(path.as_posix())

    if match:
        files = match.group(1).split("/")

        return "/".join(files[0].isdigit() and files[1:] or files)

    return path.name

# ----------------------------------------------------------------------------------------- #

def get_memory_usage(pid):
    process = psutil.Process(pid)

    if not process:
        return None, None

    return process.memory_info().rss, process.memory_percent()

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

def _find_command_line_argument(text, arg):
    pattern = re.compile(rf'-{arg}\s*(.+?)\s-') # -arg value -

    match = pattern.search(text)

    if match:
        return match.group(1).strip()

    return ""

def retrieve_launch_data(cluster_dir, save_loader):
    """
    Retrieve launch data from the cluster's log file, also saving it.

    Args:
        cluster_dir (str): the cluster path.
        save_loader (SaveLoader): save load instance.

    Returns:
        data (DotDict | None): the retrieved data or None.

    """

    log_path = Path(cluster_dir) / "Master/server_log.txt"

    if not log_path.exists():
        return None

    text  = log_path.read_text(encoding="utf-8")

    if _find_command_line_argument(text, "backup_log_count"):
        # If this one exists, it means this was launched outside of Vox.

        save_loader.save(
            persistent_storage_root = _find_command_line_argument(text, "persistent_storage_root"),
            ownerdir = _find_command_line_argument(text, "ownerdir"),
            ugc_directory = _find_command_line_argument(text, "ugc_directory"),
        )

        return save_loader.load()

    return None

def _add_to_zip(zipf, folder_path, base_path, arc_folder):
    for item in folder_path.iterdir():
        if item.is_dir():
            _add_to_zip(zipf, item, base_path)

        else:
            arcname = arc_folder / item.relative_to(base_path.parent)
            zipf.write(item, arcname)

def add_folder_to_zip(zip_filename, folder_path, arc_folder):
    with zipfile.ZipFile(zip_filename, "a", zipfile.ZIP_DEFLATED) as zipf:
        _add_to_zip(zipf, folder_path, folder_path, arc_folder)