from customtkinter import CTkFont
from tkinter.font import BOLD, NORMAL

from constants import FONT_SIZE
from strings import STRINGS

#from helpers import loadfont, resource_path

# NOTES: Not using it for now.
#loadfont(resource_path("assets/HammersmithOne-Regular.ttf").as_posix())

LANGUAGE_FONT_FAMILY = {
    "zh_CN": "Microsoft YaHei",
}

class CustomFont(CTkFont):
    def __init__(self, size, family=None, bold=True):
        super().__init__(
            family = family or LANGUAGE_FONT_FAMILY.get(STRINGS.current_language_code, "Arial"),
            size = size,
            weight = bold and BOLD or NORMAL,
        )

class Fonts:
    def create_fonts(self) -> None:
        self.ENTRY_TOOLTIP = CustomFont(FONT_SIZE.ENTRY_TOOLTIP            )
        self.ENTRY         = CustomFont(FONT_SIZE.ENTRY,         bold=False)
        self.ENTRY_ARIAL   = CustomFont(FONT_SIZE.ENTRY,         bold=False, family="Arial")
        self.INVALID_INPUT = CustomFont(FONT_SIZE.INVALID_INPUT            )
        self.CLUSTER_NAME  = CustomFont(FONT_SIZE.CLUSTER_NAME             )
        self.CLUSTER_STATS = CustomFont(FONT_SIZE.CLUSTER_STATS            )
        self.SHARD_TYPE    = CustomFont(FONT_SIZE.SHARD_TYPE               )
        self.SHARD_STATUS  = CustomFont(FONT_SIZE.SHARD_STATUS             )
        self.LAUNCH_BUTTON = CustomFont(FONT_SIZE.LAUNCH_BUTTON            )
        self.SMALL_BUTTON  = CustomFont(FONT_SIZE.SMALL_BUTTON             )
        self.VERSION       = CustomFont(FONT_SIZE.VERSION                  )
        self.TEXTBOX       = CustomFont(FONT_SIZE.TEXTBOX,       bold=False)
        self.TEXTBOX_ARIAL = CustomFont(FONT_SIZE.TEXTBOX,       bold=False, family="Arial")
        self.POPUP         = CustomFont(FONT_SIZE.POPUP,         bold=False)
        self.SHARD_TOOLTIP = CustomFont(FONT_SIZE.SHARD_TOOLTIP            )
        self.SETTING_TITLE = CustomFont(FONT_SIZE.SETTING_TITLE            )
        self.SETTING_DESC  = CustomFont(FONT_SIZE.SETTING_DESC,  bold=False)
        self.SETTING_LONG_BUTTON = CustomFont(FONT_SIZE.SETTING_LONG_BUTTON)


FONT = Fonts()