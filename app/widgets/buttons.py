from customtkinter import CTkImage, CTkButton
from PIL import Image
from constants import COLOR, Pos
from tkinter.font import NORMAL
from tkinter import DISABLED

from helpers import resource_path

class ImageButton(CTkButton):
    def __init__(self, image, image_size, pos, text=None, corner_radius=10, **kwargs):
        self.x = pos.x
        self.y = pos.y

        image = CTkImage(Image.open(resource_path(image)), size=image_size)

        super().__init__(
            image=image,
            text=text,
            corner_radius=corner_radius,
            border_spacing=0.01,
            fg_color=COLOR.GRAY,
            hover_color=COLOR.GRAY_HOVER,
            **kwargs
        )

    def show(self):
        self.place( x=self.x, y=self.y )

    def hide(self):
        self.place_forget()

    def enable(self):
        # Cursor rollback is handled by base class.
        self.configure(state=NORMAL)

    def disable(self):
        self.configure(state=DISABLED, cursor="no")

class RelativeXImageButton(ImageButton):
    def __init__(self, relx, y, **kwargs):
        self.relx = relx
        self.y = y

        super().__init__(pos=Pos(relx, y), **kwargs)

    def show(self):
        self.place( relx=self.relx, y=self.y )

class CustomButton(CTkButton):
    def __init__(self, pos, size, corner_radius=15, **kwargs):
        self.x = pos.x
        self.y = pos.y

        super().__init__(
            corner_radius = corner_radius,
            fg_color=COLOR.GRAY,
            hover_color=COLOR.GRAY_HOVER,
            text_color=COLOR.WHITE,
            width=size.w,
            height=size.h,
            **kwargs
        )

    def show(self):
        self.place( x=self.x, y=self.y )

    def hide(self):
        self.place_forget()

    def enable(self):
        # Cursor rollback is handled by base class.
        self.configure(state=NORMAL)

    def disable(self):
        self.configure(state=DISABLED, cursor="no")

    def update(self, text=None, fg_color=None, hover_color=None):
        if text:
            self.text.set(text)

        if fg_color:
            self.configure(fg_color=fg_color)

        if hover_color:
            self.configure(hover_color=hover_color)
