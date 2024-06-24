from dataclasses import dataclass
from typing import Union
import sys

# ------------------------------------------------------------------------------------ #

@dataclass
class Pos:
    x: Union[int, float]
    y: Union[int, float]

@dataclass
class Size:
    w: Union[int, float] # width
    h: Union[int, float] # height

# ------------------------------------------------------------------------------------ #

class FONT_SIZE:
    ENTRY_TOOLTIP = 15
    ENTRY = 13
    INVALID_INPUT = 12
    CLUSTER_NAME = 17
    CLUSTER_STATS = 14
    SHARD_TYPE = 20
    SHARD_STATUS = 17
    LAUNCH_BUTTON = 17
    SMALL_BUTTON = 14
    VERSION = 13
    TEXTBOX = 14
    POPUP = 13
    SHARD_TOOLTIP = 14

# ------------------------------------------------------------------------------------ #

APP_VERSION = "v1.2.0"

# ------------------------------------------------------------------------------------ #

ANNOUNCE_STR = "TheNet:SystemMessage('{msg}')"

LOGGER = hasattr(sys, '_MEIPASS') and "production" or "development"

WINDOW_MARGIN = 27
ENTRY_HEIGHT = 33

WINDOW_WIDTH = 900
CACHED_WINDOW_HEIGHT = 597

TINY_GAP = 20
SMALL_GAP = TINY_GAP * 2
LARGE_GAP = SMALL_GAP * 2
FRAME_GAP = 10
BUTTON_GAP = 7

# ------------------------------------------------------------------------------------ #

class SIZE:
    DIRECTORY_ENTRY = Size((WINDOW_WIDTH - WINDOW_MARGIN * 2 - SMALL_GAP) / 2, ENTRY_HEIGHT)
    TOKEN_ENTRY = Size(WINDOW_WIDTH - WINDOW_MARGIN * 1.5 - LARGE_GAP, ENTRY_HEIGHT)
    TOKEN_TOOLTIP = Size(ENTRY_HEIGHT, ENTRY_HEIGHT)
    SHARD_GROUP = Size(WINDOW_WIDTH - WINDOW_MARGIN * 1.6, 190)
    SHARD_STATUS_CIRCLE = Size(17, 17)
    LAUNCH_BUTTON = Size(max(150, WINDOW_WIDTH / 5), 70)
    POPUP = Size(WINDOW_WIDTH * 0.3, CACHED_WINDOW_HEIGHT * 0.1)
    CLUSTER_STATS = Size(WINDOW_WIDTH / 1.7, 30)
    LOGS_SHOW_END_BUTTON = Size(37, 37)
    LOGS_AUTO_SCROLL_SWITCH = Size(37 * 3, 37)

SIZE.FRAME = Size(SIZE.SHARD_GROUP.w - FRAME_GAP * 2, (SIZE.SHARD_GROUP.h - FRAME_GAP * 2.5) / 2)
SIZE.LOGS_BUTTON = Size(SIZE.FRAME.h / 2, SIZE.FRAME.h / 2)
SIZE.SMALL_BUTTON = Size(max(120, WINDOW_WIDTH / 7), SIZE.LAUNCH_BUTTON.h / 2 - BUTTON_GAP / 2)
SIZE.LOGS_PANEL = Size(WINDOW_WIDTH - FRAME_GAP * 2, CACHED_WINDOW_HEIGHT - FRAME_GAP * 2)
SIZE.LOGS_TEXTBOX = Size(SIZE.LOGS_PANEL.w - FRAME_GAP * 2, SIZE.LOGS_PANEL.h * 0.84 - FRAME_GAP)
SIZE.LOGS_TOP_BAR = Size(SIZE.LOGS_TEXTBOX.w, SIZE.LOGS_PANEL.h * 0.07 - FRAME_GAP * 2)
SIZE.LOGS_ENTRY = Size(SIZE.LOGS_TEXTBOX.w * 0.825 - FRAME_GAP, SIZE.LOGS_PANEL.h - (SIZE.LOGS_TEXTBOX.h + SIZE.LOGS_TOP_BAR.h) - FRAME_GAP * 4)
SIZE.LOGS_CLOSE = Size(SIZE.LOGS_TEXTBOX.w - SIZE.LOGS_ENTRY.w - FRAME_GAP, SIZE.LOGS_ENTRY.h)


assert SIZE.SMALL_BUTTON.h > FONT_SIZE.SMALL_BUTTON + 10, f"SIZE.SMALL_BUTTON.h={SIZE.SMALL_BUTTON.h} FONT_SIZE.SMALL_BUTTON + 10={FONT_SIZE.SMALL_BUTTON + 10}"

# ------------------------------------------------------------------------------------ #

class OFFSET:
    ENTRY_TOOLTIP = Pos(10, -25)
    INVALID_INPUT = Pos(20, 0)
    SHARD_TYPE = Pos(SMALL_GAP, SIZE.FRAME.h / 2 - FONT_SIZE.SHARD_TYPE / 2)
    SHARD_STATUS_MSG = Pos(SIZE.FRAME.w * 0.85, SIZE.FRAME.h / 2 - FONT_SIZE.SHARD_STATUS / 2)
    LOGS_PANEL = Pos(FRAME_GAP, FRAME_GAP)

OFFSET.SHARD_STATUS_CIRCLE = Pos(OFFSET.SHARD_STATUS_MSG.x - SMALL_GAP * 0.75, SIZE.FRAME.h / 2 + SIZE.SHARD_STATUS_CIRCLE.h / 8)
OFFSET.LOGS_BUTTON = Pos(OFFSET.SHARD_STATUS_CIRCLE.x - LARGE_GAP * 1.25, SIZE.FRAME.h / 2 - SIZE.LOGS_BUTTON.h / 2)
OFFSET.LOGS_TOP_BAR = Pos(FRAME_GAP, FRAME_GAP)
OFFSET.LOGS_TEXTBOX = Pos(FRAME_GAP, OFFSET.LOGS_TOP_BAR.y + SIZE.LOGS_TOP_BAR.h + FRAME_GAP)
OFFSET.LOGS_ENTRY = Pos(FRAME_GAP, OFFSET.LOGS_TEXTBOX.y + SIZE.LOGS_TEXTBOX.h + FRAME_GAP)
OFFSET.LOGS_CLOSE = Pos(OFFSET.LOGS_ENTRY.x + SIZE.LOGS_ENTRY.w + FRAME_GAP, OFFSET.LOGS_ENTRY.y)
OFFSET.LOGS_SHOW_END_BUTTON = Pos(SIZE.LOGS_TEXTBOX.w - SIZE.LOGS_SHOW_END_BUTTON.w - FRAME_GAP * 2, SIZE.LOGS_TEXTBOX.h - SIZE.LOGS_SHOW_END_BUTTON.w - FRAME_GAP)
OFFSET.LOGS_AUTO_SCROLL_SWITCH = Pos(SIZE.LOGS_TEXTBOX.w - SIZE.LOGS_AUTO_SCROLL_SWITCH.w - FRAME_GAP * 2, 3.5)

# ------------------------------------------------------------------------------------ #

class POS:
    GAME_DIRECTORY = Pos(WINDOW_MARGIN, WINDOW_MARGIN  - OFFSET.ENTRY_TOOLTIP.y)
    POPUP = Pos(0, 0)


POS.CLUSTER_DIRECTORY = Pos(WINDOW_MARGIN + SIZE.DIRECTORY_ENTRY.w + SMALL_GAP, POS.GAME_DIRECTORY.y)
POS.TOKEN_ENTRY = Pos(POS.GAME_DIRECTORY.x, POS.CLUSTER_DIRECTORY.y + SIZE.DIRECTORY_ENTRY.h + SMALL_GAP * 1.25)
POS.CLUSTER_NAME = Pos(WINDOW_MARGIN + FRAME_GAP * 3, POS.TOKEN_ENTRY.y + LARGE_GAP)
POS.CLUSTER_STATS = Pos(POS.CLUSTER_NAME.x + LARGE_GAP * 3.3, POS.CLUSTER_NAME.y + (FONT_SIZE.CLUSTER_NAME - FONT_SIZE.CLUSTER_STATS))
POS.SHARD_GROUP = Pos(WINDOW_MARGIN, POS.CLUSTER_NAME.y + SMALL_GAP * 0.85)
POS.LAUNCH_BUTTON = Pos(WINDOW_WIDTH - WINDOW_MARGIN - SIZE.LAUNCH_BUTTON.w, POS.SHARD_GROUP.y + SIZE.SHARD_GROUP.h + (POS.SHARD_GROUP.y - POS.TOKEN_ENTRY.y - SIZE.TOKEN_ENTRY.h - SMALL_GAP / 2))
POS.SAVE_BUTTON = Pos(POS.LAUNCH_BUTTON.x - SIZE.SMALL_BUTTON.w - SMALL_GAP, POS.LAUNCH_BUTTON.y)
POS.RESET_BUTTON = Pos(POS.SAVE_BUTTON.x - BUTTON_GAP - SIZE.SMALL_BUTTON.w, POS.SAVE_BUTTON.y)
POS.QUIT_BUTTON = Pos(POS.SAVE_BUTTON.x, POS.SAVE_BUTTON.y + BUTTON_GAP + SIZE.SMALL_BUTTON.h )
POS.ROLLBACK_BUTTON = Pos(POS.RESET_BUTTON.x, POS.QUIT_BUTTON.y)
POS.TOKEN_TOOLTIP = Pos(WINDOW_WIDTH - WINDOW_MARGIN - SIZE.TOKEN_TOOLTIP.w - FRAME_GAP, POS.TOKEN_ENTRY.y)


WINDOW_HEIGHT =  POS.LAUNCH_BUTTON.y + SIZE.LAUNCH_BUTTON.h + WINDOW_MARGIN

if WINDOW_HEIGHT != CACHED_WINDOW_HEIGHT:
    print("---------------------------------------------------------")
    print(f"Update CACHED_WINDOW_HEIGHT = {round(WINDOW_HEIGHT)}")
    print("---------------------------------------------------------")
    assert(False)

# ------------------------------------------------------------------------------------ #

class COLOR:
    DARK_GRAY = "#232323"
    GRAY = "#333333"
    GRAY_HOVER = "#393939"
    WHITE = "#D5D5D5"
    WHITE_HOVER = "#a39191"
    GREEN = "#6da269"
    YELLOW = "#ffd557"
    RED = "#9e4a44"
    RED_HOVER = "#a5504a"
    LIGHT_BLUE = "#97e1f7"

    CONSOLE_GRAY = "#a39191"

class SERVER_STATUS:
    OFFLINE  = "OFFLINE"
    STARTING = "STARTING"
    ONLINE   = "ONLINE"
    STOPPING = "STOPPING"
    RESTARTING = "RESTARTING"
