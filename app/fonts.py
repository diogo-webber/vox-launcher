from customtkinter import CTkFont
from tkinter.font import BOLD, NORMAL, Font

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

        self._pixel_font = None

    def text_width(self, text):
        """ Width of text in unscaled pixels, as CTk draws it (Tk's own measure() would treat the size as points). """

        if self._pixel_font is None:
            self._pixel_font = Font(family=self.cget("family"), size=-abs(self.cget("size")), weight=self.cget("weight"))

        return self._pixel_font.measure(text)

    def line_height(self):
        """ Height of one line of text, in unscaled pixels. """

        self.text_width("") # Makes sure the pixel font exists.

        return self._pixel_font.metrics("linespace")

    def baseline_offset(self):
        """ How far, in unscaled pixels, the baseline sits below the middle of the text's line. """

        self.text_width("") # Makes sure the pixel font exists.

        return (self._pixel_font.metrics("ascent") - self._pixel_font.metrics("descent")) / 2

    def fit_text(self, text, width):
        """ Clips text with an ellipsis so it fits in width unscaled pixels. """

        if self.text_width(text) <= width:
            return text

        while text and self.text_width(text + "…") > width:
            text = text[:-1]

        return text + "…"

class Fonts:
    def create_fonts(self) -> None:
        self.ENTRY_TOOLTIP = CustomFont(FONT_SIZE.ENTRY_TOOLTIP            )
        self.ENTRY         = CustomFont(FONT_SIZE.ENTRY,         bold=False)
        self.ENTRY_ARIAL   = CustomFont(FONT_SIZE.ENTRY,         bold=False, family="Arial")
        self.INVALID_INPUT = CustomFont(FONT_SIZE.INVALID_INPUT            )
        self.CLUSTER_NAME  = CustomFont(FONT_SIZE.CLUSTER_NAME             )
        self.LOGS_BAR      = CustomFont(FONT_SIZE.LOGS_BAR                 )
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
        self.SEARCH_RESULTS      = CustomFont(FONT_SIZE.SEARCH_RESULTS     )
        self.TOOLTIP_SMALL       = CustomFont(FONT_SIZE.TOOLTIP_SMALL,  bold=False)


FONT = Fonts()