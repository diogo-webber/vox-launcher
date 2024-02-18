from customtkinter import CTkFont
from tkinter.font import BOLD, NORMAL

from constants import FONT_SIZE
#from helpers import loadfont, resource_path

# NOTES: Not using it for now.
#loadfont(resource_path("assets/HammersmithOne-Regular.ttf").as_posix())

class CustomFont(CTkFont):
    def __init__(self, size, family="Arial", bold=True):
        super().__init__(
            family = family,
            size = size,
            weight = bold and BOLD or NORMAL,
        )

class Fonts:
    def create_fonts(self) -> None:
        self.ENTRY_TOOLTIP = CustomFont(FONT_SIZE.ENTRY_TOOLTIP            )
        self.ENTRY         = CustomFont(FONT_SIZE.ENTRY,         bold=False)
        self.INVALID_INPUT = CustomFont(FONT_SIZE.INVALID_INPUT            )
        self.CLUSTER_NAME  = CustomFont(FONT_SIZE.CLUSTER_NAME             )
        self.CLUSTER_STATS = CustomFont(FONT_SIZE.CLUSTER_STATS            )
        self.SHARD_TYPE    = CustomFont(FONT_SIZE.SHARD_TYPE               )
        self.SHARD_STATUS  = CustomFont(FONT_SIZE.SHARD_STATUS             )
        self.LAUNCH_BUTTON = CustomFont(FONT_SIZE.LAUNCH_BUTTON            )
        self.SMALL_BUTTON  = CustomFont(FONT_SIZE.SMALL_BUTTON             )
        self.VERSION       = CustomFont(FONT_SIZE.VERSION                  )
        self.TEXTBOX       = CustomFont(FONT_SIZE.TEXTBOX,       bold=False)
        self.POPUP         = CustomFont(FONT_SIZE.POPUP,         bold=False)
        self.SHARD_TOOLTIP = CustomFont(FONT_SIZE.SHARD_TOOLTIP            )


FONT = Fonts()