from tkinter import Toplevel

import customtkinter as ctk
from PIL import Image

from constants import COLOR, Pos, Size
from strings import STRINGS
from fonts import FONT
from widgets.buttons import CustomButton
from widgets.misc import TOOLTIP_TRANSPARENT_COLOR
from helpers import resource_path

class DropdownPopup:
    """ Floating list under a widget. It is its own window, so what is behind its rounded corners shows through. """

    def __init__(self, root, anchor, width, height, x_offset=0, gap=6):
        self.root = root
        self.anchor = anchor
        self.x_offset = x_offset
        self.gap = gap
        self.visible = False

        self.window = Toplevel(root)
        self.window.withdraw()
        self.window.wm_overrideredirect(True)
        self.window.transient(root)
        self.window.configure(bg=TOOLTIP_TRANSPARENT_COLOR)
        self.window.wm_attributes("-transparentcolor", TOOLTIP_TRANSPARENT_COLOR)

        # Fixes the size, as the window would otherwise shrink to whatever the list holds.
        self._holder = ctk.CTkFrame(master=self.window, width=width, height=height, fg_color="transparent")
        self._holder.pack_propagate(False)
        self._holder.pack()

        self.list = ctk.CTkScrollableFrame(
            master=self._holder,
            fg_color=COLOR.GRAY,
            bg_color=TOOLTIP_TRANSPARENT_COLOR,
            corner_radius=10,
        )

        self.list.pack(fill="both", expand=True)

        # The popup is positioned in screen coordinates, so it has to follow the window around.
        root.bind("<Configure>", self._on_root_configure, add="+")

    def show(self):
        scale = self.anchor._apply_widget_scaling(1.0)

        x = self.anchor.winfo_rootx() + round(self.x_offset * scale)
        y = self.anchor.winfo_rooty() + self.anchor.winfo_height() + round(self.gap * scale)

        self.window.geometry(f"+{x}+{y}")
        self.window.deiconify()
        self.window.lift()

        self.visible = True

    def hide(self):
        self.window.withdraw()

        self.visible = False

    def owns(self, widget):
        return str(widget).startswith(str(self.window))

    def _on_root_configure(self, event):
        if self.visible and event.widget is self.root:
            self.hide()

class OverlaysMixin:
    """ For buttons with labels drawn over them: keeps the labels' background in step with the button's hover color. """

    overlay_labels = ()
    overlay_backdrops = ()

    def _on_enter(self, event=None):
        super()._on_enter(event)

        self._tint_overlay()

    def _on_leave(self, event=None):
        super()._on_leave(event)

        self._tint_overlay()

    def _tint_overlay(self):
        color = self._canvas.itemcget("inner_parts", "fill")

        for label in self.overlay_labels:
            label.configure(fg_color=color)

        # Rounded widgets with a color of their own draw their corners in this one.
        for widget in self.overlay_backdrops:
            widget.configure(bg_color=color)


class OverlaidButton(OverlaysMixin, CustomButton):
    pass


def bind_overlay(button, *tinted, forward=(), backdrops=()):
    """ Widgets drawn over an OverlaysMixin button swallow its events, so they are handed back to it. The tinted ones also follow its hover color, and the backdrops' corners do. """

    button.overlay_labels = tinted
    button.overlay_backdrops = backdrops

    for widget in (*tinted, *forward, *backdrops):
        widget.bind("<ButtonRelease-1>", button._on_release)
        widget.bind("<Enter>", button._on_enter)
        widget.bind("<Leave>", button._on_leave)


class RightAnchoredImageButton(CustomButton):
    # The arrow image has blank space around the chevron, which the right margin gives back.
    ARROW_MARGIN_TRIM = 1

    def _create_grid(self):
        super()._create_grid()

        if self._image_label is not None:
            self._image_label.grid(row=2, column=3, sticky="e")
            self.grid_columnconfigure(3, weight=0)
            self.grid_columnconfigure(2, weight=999999)

            # Keeps the chevron a little further from the right edge than the text is from the left one.
            self.grid_columnconfigure(4, minsize=self._apply_widget_scaling(max(0, self._corner_radius - self.ARROW_MARGIN_TRIM)))


class OverlaidRightAnchoredButton(OverlaysMixin, RightAnchoredImageButton):
    pass


class CustomDropdown():
    def __init__(self, master, options, default, on_selected_option=None):
        self.master = master
        self.options = options
        self.selected_value = ctk.StringVar(value=STRINGS.LANGUAGES[default])
        self.selected_code = default
        self.on_selected_option = on_selected_option

        image_size = 19.5

        image = ctk.CTkImage(Image.open(resource_path("assets/dropdown.png")), size=(image_size, image_size))

        # Create toggle button
        self.button = RightAnchoredImageButton(
            master=self.master,
            textvariable=self.selected_value,
            command=self.toggle_menu,
            font=FONT.ENTRY,
            anchor="w",
            size=Size(200, 40),
            pos=Pos(0, 0),
            image=image,
            compound="right",
        )

        # Max number of items and height setup
        max_visible_items = 5
        item_height = 30
        menu_height = item_height * max_visible_items - 10

        self.popup = DropdownPopup(
            root=self.master.winfo_toplevel(),
            anchor=self.button,
            width=200,
            height=menu_height,
            x_offset=20,
        )

        self.menu_frame = self.popup.list

        # Populate options
        for i, (code, name) in enumerate(self.options):
            button = CustomButton(
                master=self.menu_frame,
                text=name,
                command=lambda code=code, name=name: self.select_option(code, name),
                corner_radius=8,
                font=FONT.ENTRY,
                anchor="w",
                size=Size(190, item_height),
                pos=Pos(0, 0),
            )
            button.pack(fill="x")

        # Dismiss dropdown when clicking outside
        self.master.winfo_toplevel().bind("<Button-1>", self._on_root_click, add="+")

    def _on_root_click(self, event):
        if not self.popup.visible:
            return

        try:
            widget = self.master.winfo_toplevel().winfo_containing(event.x_root, event.y_root)
            if self.popup.owns(widget) or str(widget).startswith(str(self.button)):
                return
        except (AttributeError, TypeError):
            pass

        self.popup.hide()

    def toggle_menu(self):
        """Toggle visibility of the menu"""
        if self.popup.visible:
            self.popup.hide()
        else:
            self.popup.show()

    def select_option(self, code, name):
        """Select an option and close the menu"""

        self.selected_value.set(name)
        self.selected_code = code
        self.popup.hide()

        if self.on_selected_option:
            self.on_selected_option(code, name)
