from pathlib import Path
import winreg, ctypes
from dataclasses import dataclass
import ctypes.wintypes
import webbrowser
import re, json, sys, math, base64
import logging
import shlex
import threading
import psutil, os, zipfile, shutil, subprocess
from urllib.parse import quote as encode_for_url
from customtkinter import set_window_scaling, set_widget_scaling

from constants import LOGGER

logger = logging.getLogger(LOGGER)

# ----------------------------------------------------------------------------------------- #

@dataclass
class TextHighlightData():
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

    def __getattr__(self, key):
        # Only called for missing attributes; None lets old save files lack newer keys.
        if key.startswith("_"):
            raise AttributeError(key)

        return None

    def __getitem__(self, key):
        return getattr(self, key, None)

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

        try:
            self.file.parent.mkdir(exist_ok=True, parents=True)

            self.file.write_text(
                json.dumps(
                    kwargs,
                    sort_keys = True,
                    indent = 4,
                    ensure_ascii = False
                ),
                encoding="utf-8",
                errors="backslashreplace"
            )

        except OSError as e:
            logger.error(f"Failed to write the save file '{self.file.name}': {e}")

    def load(self):
        """
        Loads self.file and returns the data loaded.

        Returns:
            None if the file doesn't exists, otherwise a DotDict instance containing the data loaded.
        """

        try:
            data = json.loads(self.file.read_text(encoding="utf-8", errors="backslashreplace"))

        except FileNotFoundError:
            return

        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Failed to read the save file '{self.file.name}', its contents will be ignored: {e}")
            return

        if not isinstance(data, dict):
            logger.error(f"The save file '{self.file.name}' is malformed, its contents will be ignored.")
            return

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

    pattern = re.compile(r'VoxLauncherData=(\{.+?\})')
    matches = pattern.findall(text)

    if not matches:
        return

    if len(matches) > 1:
        # Data overload! Grab new data.
        server.execute_command("VoxLauncher_GetServerStats()")
        return

    string = matches[0].strip()

    try:
        return json.loads(string)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse Vox Launcher data from the server: {e}")
        return None

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

    try:
        text = file.read_text(encoding="utf-8", errors="backslashreplace")

    except FileNotFoundError:
        return None

    except OSError as e:
        logger.warning(f"Failed to read '{file}': {e}")
        return None

    # Anchored, so commented out lines and keys merely ending in 'key' are skipped.
    pattern = re.compile(rf'^[ \t]*{re.escape(key)}[ \t]*=(.*)$', re.MULTILINE)

    match = pattern.search(text)

    return match.group(1).strip() if match else None

DEFAULT_MAX_SNAPSHOTS = 6

def _get_max_rollbacks(cluster_settings):
    """
    Reads an .ini file and returns the max_snapshots value.

    Args:
        cluster_settings (Path): a .ini file.

    Returns:
        value (int): cluster_settings's max_snapshots or DEFAULT_MAX_SNAPSHOTS.
    """

    max_snapshots = get_key_from_ini_file(cluster_settings, "max_snapshots")

    try:
        return max(1, int(max_snapshots))

    except (TypeError, ValueError):
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

def validate_game_directory(directory) -> bool:
    """
    Checks if directory holds a dedicated server executable.

    Args:
        directory (Path, str): the game directory path.

    Returns:
        valid (bool): valid or not.
    """

    directory = Path(directory)

    if not directory.exists():
        logger.debug(f"Invalid game directory: '{directory}' doesn't exist.")
        return False

    if not any((directory / child).exists() for child in GAME_DIRECTORY_ONE_OF_CHILDREN):
        logger.debug(f"Invalid game directory: '{directory}' holds none of {GAME_DIRECTORY_ONE_OF_CHILDREN}.")
        return False

    return True

# ----------------------------------------------------------------------------------------- #

TOKEN_PATTERN = r"^pds-g\^KU.+\^.+"

def is_valid_token(token: str) -> bool:
    """
    Validates if the given token string matches the expected format:
    pds-g^KU_.........^................................=

    Args:
        token (str): The token string to validate.

    Returns:
        bool: True if valid, False otherwise.
    """

    return bool(re.match(TOKEN_PATTERN, token))

# ----------------------------------------------------------------------------------------- #

class INVALID:
    """ Reason keys for entry validation, resolved against STRINGS.ENTRY.INVALID. """

    EMPTY = "EMPTY"
    MISSING = "MISSING"
    NO_EXECUTABLE = "NO_EXECUTABLE"
    IS_WORLD = "IS_WORLD"
    NO_CLUSTERS = "NO_CLUSTERS"
    INCOMPLETE_WORLD = "INCOMPLETE_WORLD"
    CLOUD_SAVES = "CLOUD_SAVES"
    WRONG_LOCATION = "WRONG_LOCATION"
    TOKEN_FORMAT = "TOKEN_FORMAT"
    TOKEN_REJECTED = "TOKEN_REJECTED"

def get_game_directory_error(directory: str):
    """ Returns an INVALID reason for the game directory, or None when it's usable. """

    if not directory.strip():
        return INVALID.EMPTY

    if not Path(directory).exists():
        return INVALID.MISSING

    if not validate_game_directory(directory):
        return INVALID.NO_EXECUTABLE

    return None

def is_cluster_folder(folder):
    """ Whether folder is a world the launcher can run: it needs a cluster.ini and a Master shard. """

    folder = Path(folder)

    return (folder / "cluster.ini").exists() and (folder / "Master").exists()

def list_clusters(directory):
    """
    Lists the usable clusters inside a clusters directory.

    Args:
        directory (Path, str): the folder holding the clusters.

    Returns:
        list: (folder name, display name) tuples sorted by display name. Only folders with a cluster.ini and a Master shard are listed.
    """

    try:
        folders = list(Path(directory).iterdir())

    except OSError as e:
        logger.warning(f"Failed to list the clusters in '{directory}': {e}")
        return []

    clusters = []

    for folder in folders:
        if folder.is_dir() and is_cluster_folder(folder):
            clusters.append((folder.name, get_sanitized_cluster_name(folder / "cluster.ini") or folder.name))

    return sorted(clusters, key=lambda cluster: (cluster[1].lower(), cluster[0].lower()))

def get_clusters_directory_error(directory: str):
    """ Returns an INVALID reason for the folder holding the clusters, or None when it's usable. """

    if not directory.strip():
        return INVALID.EMPTY

    path = Path(directory)

    if any(part.lower() == "cloudsaves" for part in path.parts):
        return INVALID.CLOUD_SAVES

    if not path.is_dir():
        return INVALID.MISSING

    # Old versions asked for the world itself, so a world picked here is a likely mistake.
    if (path / "cluster.ini").exists():
        return INVALID.IS_WORLD

    # The same rule as for a cluster, as if one lived inside this folder.
    if not is_config_directory(get_cluster_launch_paths(path / "cluster")["conf_dir"]):
        return INVALID.WRONG_LOCATION

    if not list_clusters(path):
        return INVALID.NO_CLUSTERS

    return None

def get_cluster_error(directory: str):
    """ Returns an INVALID reason for the selected world's folder, or None when it's usable. """

    if not directory.strip():
        return INVALID.EMPTY

    path = Path(directory)

    if not path.is_dir():
        return INVALID.MISSING

    if not is_cluster_folder(path):
        return INVALID.INCOMPLETE_WORLD

    return None

def get_token_error(token: str):
    """ Returns an INVALID reason for the server token, or None when it's usable. """

    if not token.strip():
        return INVALID.EMPTY

    if not is_valid_token(token):
        return INVALID.TOKEN_FORMAT

    return None

# ----------------------------------------------------------------------------------------- #

def get_app_logs():
    file = resource_path("logs/applog.txt")

    try:
        return file.read_text(encoding="utf-8", errors="backslashreplace")

    except OSError:
        return "No logs available."

# ----------------------------------------------------------------------------------------- #

def open_klei_account_page(*args, **kwargs):
    """ Opens Klei dedicated servers website in the default browser. """

    webbrowser.open("https://accounts.klei.com/account/game/servers?game=DontStarveTogether", new=0, autoraise=True)

def open_url(url):
    """ Opens an url in the default browser. """

    webbrowser.open(url, new=0, autoraise=True)

def open_github_issue(template="bug_report", traceback=None, include_applog=False):
    """
    Opens the Vox Launcher GitHub issues page with a pre-filled template.

    Args:
        template (str): Issue template name (without .yml). Default is "bug_report".
        traceback (str, optional): Traceback to include.
        include_applog (bool): If True, includes app logs.
    """

    MAX_URL_LENGTH = 8000

    url = f"https://github.com/diogo-webber/vox-launcher/issues/new?template={template}.yml"

    for name, value in (("traceback", traceback), ("applogs", include_applog and get_app_logs() or None)):
        if not value:
            continue

        # Trim the payload itself, so truncating can't cut a percent escape in half.
        while value:
            field = f"&{name}={encode_for_url(value)}"

            if len(url) + len(field) <= MAX_URL_LENGTH:
                url += field
                break

            value = value[len(value) // 2:]

    webbrowser.open(url, new=0, autoraise=True)

def open_folder(path):
    """ Opens a Windows explorer instance on this path  """
    if isinstance(path, str):
        path = Path(path)

    if path.exists():
        os.startfile(path)

def open_file(path):
    """ Opens a file  """

    if isinstance(path, str):
        path = Path(path)

    if path.exists():
        os.startfile(path)


# ----------------------------------------------------------------------------------------- #

def disable_bind(event):
    return "break"

# ----------------------------------------------------------------------------------------- #

LUA_FOLDER = Path(__file__).absolute().parent / "lua"

lua_file_cache = {}
_lua_cache_lock = threading.Lock()

def load_lua_file(filename, **kwargs):
    """
    Loads a .lua file and returns its content, joining its lines.

    Args:
        filename (str): the filename, without suffix. Must be inside lua/ folder.
        **kwargs: Optional keyword arguments to replace {{key}} placeholders in the Lua file.

    Returns:
        text (str or None): the text if the file exists, None otherwise.
    """
    cache_key = (filename, tuple(sorted(kwargs.items())))

    with _lua_cache_lock:
        if cache_key in lua_file_cache:
            return lua_file_cache[cache_key]

    file = LUA_FOLDER / f"{filename}.lua"

    if file.exists():
        text = file.read_text(encoding="utf-8", errors="backslashreplace")

        # Remove single-line comments (including newline)
        text = re.sub(r'--.*?(?:\r\n|\r|\n)', '', text)

        # Replace placeholders {{key}} with values from kwargs
        text = re.sub(r"\{\{(\w+)\}\}", lambda m: kwargs.get(m.group(1), m.group(0)), text)

        # Join lines, remove excessive whitespace
        text = " ".join(text.split())

        with _lua_cache_lock:
            lua_file_cache[cache_key] = text

        return text
    else:
        logger.error(f"Failed to load the lua file '{file}': it doesn't exist.")

        return None

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

SHARD_ORDER = { "Master": 0, "Caves": 1 }

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

    try:
        entries = list(cluster.iterdir())

    except OSError as e:
        logger.warning(f"Failed to list the shards in '{cluster}': {e}")
        return shards

    for directory in entries:
        if directory.is_dir() and (directory / "server.ini").exists():
            shards.append(directory.name)

    # Master first, then Caves, then the rest alphabetically.
    return sorted(shards, key=lambda name: (SHARD_ORDER.get(name, 2), name.lower()))

# ----------------------------------------------------------------------------------------- #

CONFIG_DIRECTORY_NAMES = ( "DoNotStarveTogether", "DoNotStarveTogetherBetaBranch" )

def is_config_directory(name):
    """ Whether name is the folder the game keeps its clusters in. """

    return bool(name) and name.lower().startswith("donotstarvetogether")

def get_cluster_launch_paths(path):
    """
    Splits a cluster directory into the command line arguments the server needs.
    The game resolves a cluster as <persistent_storage_root>/<conf_dir>[/<ownerdir>]/<cluster>.

    Args:
        path (Path, str): the cluster path.

    Returns:
        dict: "cluster", "ownerdir", "conf_dir" and "persistent_storage_root" keys.
    """

    path = Path(path).resolve()

    paths = { "cluster": path.name, "ownerdir": None, "conf_dir": None, "persistent_storage_root": None }

    parent = path.parent

    # Some users have their clusters inside a numeric (user id) folder.
    if parent.name.isdigit():
        paths["ownerdir"] = parent.name
        parent = parent.parent

    # parent.name is empty once we reach a drive/UNC root.
    if parent.name and parent.parent != parent:
        paths["conf_dir"] = parent.name
        paths["persistent_storage_root"] = str(parent.parent)

    return paths

STEAM_APP_ID = "322330"

def get_ugc_directory(game_directory):
    """
    Determines the Steam Workshop (ugc) folder that holds the subscribed mods.

    Args:
        game_directory (str, Path, None): the game install path.

    Returns:
        str | None: the workshop path, or None if the game isn't inside a Steam library.
    """

    if not game_directory:
        return None

    # <library>/steamapps/common/Don't Starve Together -> <library>/steamapps
    steamapps = Path(game_directory).resolve().parent.parent

    if steamapps.name.lower() != "steamapps":
        logger.debug(f"No workshop directory: '{game_directory}' isn't inside a Steam library.")
        return None

    workshop = steamapps / "workshop"

    if not (workshop / "content" / STEAM_APP_ID).is_dir():
        logger.debug(f"No workshop directory: no subscribed mods found in '{workshop}'.")
        return None

    return str(workshop)

def split_launch_options(text):
    """
    Splits user provided launch options into argv entries.

    Args:
        text (str): the raw launch options.

    Returns:
        list: the individual arguments.
    """

    lexer = shlex.shlex(text or "", posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    lexer.escape = "" # On Windows '\' is a path separator, never an escape character.

    try:
        return list(lexer)

    except ValueError as e:
        logger.warning(f"Failed to parse the custom launch options ({e}), falling back to a whitespace split.")

        return (text or "").split()

def redact_token(args):
    """
    Hides the value of every -token argument, so the command line can be logged.

    Args:
        args (list): the server arguments.

    Returns:
        list: the arguments, with the token values replaced.
    """

    redacted = list(args)

    for index, arg in enumerate(redacted[:-1]):
        if arg == "-token":
            redacted[index + 1] = "<hidden>"

    return redacted

# ----------------------------------------------------------------------------------------- #

def is_newer_version(remote, local):
    """
    Compares two version strings, ignoring any leading 'v' and any suffix.

    Args:
        remote (str): the version to check, e.g. "v1.4.1".
        local (str): the version to check against, e.g. "v1.4.0".

    Returns:
        bool: True when remote is a higher version than local.
    """

    def parse(version):
        return [int(part) for part in re.findall(r"\d+", version or "")]

    remote_parts = parse(remote)
    local_parts = parse(local)

    if not remote_parts:
        return False

    # Zero padded, so "1.4" and "1.4.0" compare as equal.
    length = max(len(remote_parts), len(local_parts))

    remote_parts += [0] * (length - len(remote_parts))
    local_parts  += [0] * (length - len(local_parts))

    return remote_parts > local_parts

# ----------------------------------------------------------------------------------------- #

def get_memory_usage(pid):
    try:
        process = psutil.Process(pid)
        return process.memory_info().rss, process.memory_percent()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None, None

# ----------------------------------------------------------------------------------------- #

class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

PROTECTED_PREFIX = "dpapi:"

def _run_dpapi(function, data):
    """ Runs CryptProtectData/CryptUnprotectData over bytes, returning the result bytes or None. """

    buffer = ctypes.create_string_buffer(data, len(data))
    source = _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    result = _DataBlob()

    if not function(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(result)):
        return None

    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(result.pbData)

def protect_text(text):
    """
    Encrypts text with the Windows user account (DPAPI), so it is unreadable outside of it.

    Args:
        text (str): the text to protect.

    Returns:
        str: a PROTECTED_PREFIX tagged string, or the text itself when it is empty or encryption fails.
    """

    if not text:
        return text

    encrypted = _run_dpapi(ctypes.windll.crypt32.CryptProtectData, text.encode("utf-8"))

    if encrypted is None:
        logger.warning("Failed to encrypt the text with DPAPI, it will be stored as plain text.")
        return text

    return PROTECTED_PREFIX + base64.b64encode(encrypted).decode("ascii")

def unprotect_text(text):
    """
    Reverses protect_text. Text without the PROTECTED_PREFIX (older saves) is returned as is.

    Args:
        text (str): the stored text.

    Returns:
        str: the original text, or an empty string if it can't be decrypted by this user.
    """

    if not text or not text.startswith(PROTECTED_PREFIX):
        return text

    try:
        decrypted = _run_dpapi(ctypes.windll.crypt32.CryptUnprotectData, base64.b64decode(text[len(PROTECTED_PREFIX):]))

    except ValueError:
        decrypted = None

    if decrypted is None:
        logger.warning("Failed to decrypt the stored text, it was saved by another Windows user.")
        return ""

    return decrypted.decode("utf-8")

# ----------------------------------------------------------------------------------------- #

def terminate_process_tree(pid, timeout=3):
    """
    Terminates a process and all of its children, killing whatever ignores the request.

    Args:
        pid (int): the root process id.
        timeout (int, float): seconds to wait before force killing.
    """

    try:
        root = psutil.Process(pid)
        processes = root.children(recursive=True) + [root]

    except psutil.NoSuchProcess:
        return

    for process in processes:
        try:
            process.terminate()
        except psutil.NoSuchProcess:
            pass

    _, alive = psutil.wait_procs(processes, timeout=timeout)

    for process in alive:
        try:
            process.kill()
        except psutil.NoSuchProcess:
            pass

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

    except OSError as e:
        logger.debug(f"Failed to read the game directory from the registry key 'Steam App 322330\\InstallLocation': {e}")

    try:
        # Open the Steam registry key.
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            # Read the Steam installation path from the registry
            steam_path, _ = winreg.QueryValueEx(key, "SteamPath")

            directory = Path(steam_path) / "steamapps/common/Don't Starve Together"

            if validate_game_directory(directory):
                return directory

    except OSError as e:
        logger.debug(f"Failed to read the game directory from the registry key 'Software\\Valve\\Steam\\SteamPath': {e}")

    return None

CSIDL_PERSONAL = 5       # Documents
SHGFP_TYPE_CURRENT = 0   # Get current, not default value

def _get_documents_folder():
    """
    Determines the user's document directory.

    Returns:
        directory (Path, None): the documents directory path or None.
    """

    buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
    result = ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)

    if result != 0 or not buf.value:
        logger.debug(f"SHGetFolderPathW failed to resolve the Documents folder (0x{result & 0xFFFFFFFF:08X}).")
        return None

    return Path(buf.value)

def get_clusters_directory():
    """
    Attempts to determine the user's cluster persistent storage.

    Returns:
        directory (Path, None): the directory path or None.
    """

    documents = _get_documents_folder()

    if documents is None:
        return None

    for config_directory in CONFIG_DIRECTORY_NAMES:
        dst_directory = documents / "Klei" / config_directory

        if not dst_directory.exists():
            continue

        if (dst_directory / "client.ini").exists():
            return dst_directory

        # Some users have their clusters inside a numeric folder.
        for directory in dst_directory.iterdir():
            if directory.is_dir() and directory.name.isdigit() and (directory / "client.ini").exists():
                return directory

    return None

def _find_command_line_argument(text, arg):
    # Every argument is logged on a single line, so the value ends at the next ' -flag'.
    pattern = re.compile(rf'(?:^|\s)-{re.escape(arg)}\s+(.+?)(?=\s-|\s*$)', re.MULTILINE)

    match = pattern.search(text)

    if match:
        return match.group(1).strip()

    return ""

def retrieve_launch_data(cluster_dir, save_loader):
    """
    Retrieve launch data from the cluster's log file or any sibling cluster log files.

    Args:
        cluster_dir (str): the cluster path.
        save_loader (SaveLoader): save loader instance.

    Returns:
        data (DotDict | None): the retrieved data or None.
    """

    cluster_path = Path(cluster_dir)

    # First, check current cluster.
    data = _check_log_file(cluster_path, save_loader)

    if data:
        return data

    # Then, check sibling clusters in parent folder.
    try:
        siblings = list(cluster_path.parent.iterdir())

    except OSError as e:
        logger.warning(f"Failed to list the clusters next to '{cluster_path}': {e}")
        return None

    for sibling_cluster in siblings:
        if sibling_cluster.is_dir() and sibling_cluster != cluster_path:
            data = _check_log_file(sibling_cluster, save_loader)

            if data:
                return data

    return None

# The command line is logged in the first few lines, but server logs can reach hundreds of MB.
LOG_HEADER_SIZE = 64 * 1024

def _check_log_file(cluster_path, save_loader):
    """
    Checks the Master/server_log.txt in a cluster folder.

    Args:
        cluster_path (Path): path to the cluster.
        save_loader (SaveLoader): save loader instance.

    Returns:
        data (DotDict | None): retrieved data or None.
    """

    log_path = cluster_path / "Master/server_log.txt"

    try:
        with log_path.open(encoding="utf-8", errors="backslashreplace") as file:
            text = file.read(LOG_HEADER_SIZE)

    except OSError:
        return None

    if _find_command_line_argument(text, "backup_log_count"):
        # If backup_log_count exists, it's likely that this cluster was launched outside of Vox.
        save_loader.save(
            ugc_directory=_find_command_line_argument(text, "ugc_directory"),
        )

        logger.info(f"Recovered the launch data from '{log_path}'.")

        return save_loader.load()

    return None

def _add_to_zip(zipf, folder_path, base_path, arc_folder):
    for item in folder_path.iterdir():
        if item.is_dir():
            _add_to_zip(zipf, item, base_path, arc_folder)

        else:
            arcname = arc_folder / item.relative_to(base_path.parent)
            zipf.write(item, arcname)

def add_folder_to_zip(zip_filename, folder_path, arc_folder):
    with zipfile.ZipFile(zip_filename, "a", zipfile.ZIP_DEFLATED) as zipf:
        _add_to_zip(zipf, folder_path, folder_path, arc_folder)

# Folders of the data directory that belong to the user and survive an update.
_UPDATE_KEPT_FOLDERS = ("savedata", "logs")

def can_update_in_place():
    """ In-place updates only make sense for the packaged app. """

    return bool(getattr(sys, "frozen", False))

def stage_update(zip_bytes):
    """
    Extracts a release zip and writes the script that installs it once this process exits.

    Args:
        zip_bytes (bytes): the content of the release zip.

    Returns:
        Path: the script to run, see launch_update_script().
    """

    import io, tempfile

    app_dir = Path(sys.executable).resolve().parent
    work_dir = Path(tempfile.mkdtemp(prefix="vox_update_"))
    staging = work_dir / "staging"

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zipf:
        zipf.extractall(staging)

    if not (staging / Path(sys.executable).name).exists():
        raise FileNotFoundError("The downloaded package does not contain the launcher executable.")

    # The new version must not overwrite the user's data.
    for folder in _UPDATE_KEPT_FOLDERS:
        shutil.rmtree(staging / "appdata" / folder, ignore_errors=True)

    script = work_dir / "update.bat"

    # Waits for this process to exit, copies the new files over and starts the new version.
    script.write_bytes((
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        f'powershell -NoProfile -NonInteractive -Command "Wait-Process -Id {os.getpid()} -ErrorAction SilentlyContinue"\r\n'
        f'robocopy "{staging}" "{app_dir}" /E /R:30 /W:1 /NFL /NDL /NJH /NJS >nul\r\n'
        f'start "" "{Path(sys.executable).resolve()}"\r\n'
        f'rmdir /s /q "{work_dir}"\r\n'
    ).encode("utf-8"))

    return script

def launch_update_script(script):
    """ Starts the update script detached from this process, so it outlives it. """

    # The hidden console is inherited by the script's child processes, so none opens a window.
    CREATE_NO_WINDOW = 0x08000000
    CREATE_NEW_PROCESS_GROUP = 0x00000200

    subprocess.Popen(
        ["cmd", "/c", str(script)],
        creationflags=CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )

def set_debug_scale(scale):
    set_window_scaling(scale)
    set_widget_scaling(scale)

def redraw_safe_size(widget, value, grow_only=False):
    """
    Nearest whole size to value that CTk can draw rounded corners on cleanly.

    CTk rescales a widget's pixel size back to logical units on every <Configure> and redraws
    from that, truncating in both directions. Sizes that lose a pixel there, or that land on an
    odd pixel count, get their corner arcs drawn half a pixel off from the straight edges, which
    reads as a dent.

    Args:
        widget (CTkBaseClass): the widget the size will be applied to.
        value (int, float): the wanted size, in logical pixels.
        grow_only (bool): never return less than value, for sizes that would clip their content.

    Returns:
        size (int): the closest usable size, preferring the smaller one on a tie.
    """

    value = math.ceil(value) if grow_only else int(value)

    if value <= 0:
        return value

    def usable(candidate):
        scaled = widget._apply_widget_scaling(candidate)

        return scaled % 2 == 0 and widget._reverse_widget_scaling(scaled) == candidate

    for offset in range(64):
        for candidate in (value + offset,) if grow_only else (value - offset, value + offset):
            if candidate > 0 and usable(candidate):
                return candidate

    return value

def read_file_nonblocking(file: Path, callback):
    def worker():
        if file.exists():
            try:
                content = file.read_text(encoding="utf-8", errors="backslashreplace")

            except Exception as e:
                logger.warning(f"Failed to read '{file}': {e}")
                content = ""
        else:
            content = ""

        callback(content)

    threading.Thread(target=worker, daemon=True).start()

# ------------------------------------------------------------------------------------------ #

_INVALID_UNICODE_RANGES = [
    (983040, 983089),  # Emoji
    (57600,   57606),  # Mouse
]

_CUSTOM_UNICODE_PATTERN = re.compile("[" + "".join(f"{chr(start)}-{chr(end)}" for start, end in _INVALID_UNICODE_RANGES) + "]")

def _get_sanitized_ini_text(config_file, key):
    text = get_key_from_ini_file(config_file, key) or ""

    # Remove custom unicode characters.
    cleaned = _CUSTOM_UNICODE_PATTERN.sub("", text)

    # Remove duplicated whitespaces.
    cleaned = re.sub(r'\s+', " ", cleaned).strip()

    return cleaned

def get_sanitized_cluster_name(config_file):
    return _get_sanitized_ini_text(config_file, "cluster_name")

# ------------------------------------------------------------------------------------------ #

_MOD_KEY_PATTERN = re.compile(r'\["(workshop-\d+)"\]')
_MOD_ENABLED_PATTERN = re.compile(r'enabled\s*=\s*true')

def count_enabled_mods(cluster):
    """
    Counts the workshop mods enabled in any shard of a cluster, from its modoverrides.lua files.

    Args:
        cluster (Path): the cluster path.

    Returns:
        count (int): how many different mods are enabled.
    """

    enabled = set()

    for shard in get_shard_names(cluster):
        try:
            text = (cluster / shard / "modoverrides.lua").read_text(encoding="utf-8", errors="backslashreplace")

        except OSError:
            continue

        keys = list(_MOD_KEY_PATTERN.finditer(text))

        for index, key in enumerate(keys):
            # A mod's block runs until the next mod's key.
            end = keys[index + 1].start() if index + 1 < len(keys) else len(text)

            if _MOD_ENABLED_PATTERN.search(text, key.end(), end):
                enabled.add(key.group(1))

    return len(enabled)

def get_last_played(cluster):
    """
    Finds when a cluster was last saved, from its newest save file.

    Args:
        cluster (Path): the cluster path.

    Returns:
        timestamp (float, None): the time, or None if it has no saves.
    """

    latest = None

    for shard in get_shard_names(cluster):
        try:
            for file in (cluster / shard / "save").rglob("*"):
                if file.is_file():
                    modified = file.stat().st_mtime

                    latest = modified if latest is None else max(latest, modified)

        except OSError as e:
            logger.debug(f"Failed to read the saves of '{cluster / shard}': {e}")

    return latest

@dataclass
class ClusterDetails:
    """ What the world list shows about a cluster. """

    folder: str
    name: str
    description: str
    game_mode: str
    mods: int
    last_played: float

def get_cluster_details(directory, folder):
    """
    Reads the details of a cluster.

    Args:
        directory (Path, str): the folder holding the clusters.
        folder (str): the cluster's folder name.

    Returns:
        ClusterDetails: the cluster's name, description, game mode, enabled mods and last played time.
    """

    cluster = Path(directory) / folder
    config_file = cluster / "cluster.ini"

    return ClusterDetails(
        folder=folder,
        name=get_sanitized_cluster_name(config_file) or folder,
        description=_get_sanitized_ini_text(config_file, "cluster_description"),
        game_mode=(get_key_from_ini_file(config_file, "game_mode") or "survival").lower(), # The game's default.
        mods=count_enabled_mods(cluster),
        last_played=get_last_played(cluster),
    )
