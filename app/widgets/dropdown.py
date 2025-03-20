import customtkinter as ctk
from PIL import Image

from constants import COLOR, Pos, Size
from strings import STRINGS
from fonts import FONT, LANGUAGE_FONT_FAMILY
from widgets.buttons import CustomButton
from helpers import resource_path

class RightAnchoredImageButton(CustomButton):
    def _create_grid(self):
        super()._create_grid()

        if self._image_label is not None:
            self._image_label.grid(row=2, column=3, sticky="e")
            self.grid_columnconfigure(3, weight=0)
            self.grid_columnconfigure(2, weight=999999)


class CustomDropdown():
    def __init__(self, master, options, default, on_selected_option=None):
        self.master = master
        self.options = options
        self.selected_value = ctk.StringVar(value=STRINGS.LANGUAGES[default])
        self.selected_code = default
        self.on_selected_option = on_selected_option

        image_size = self.master._apply_widget_scaling(13)
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

        # ====== Container to control size ======
        self.menu_container = ctk.CTkFrame(self.master, width=200, height=menu_height, corner_radius=10)
        self.menu_container.pack_propagate(False)  # Prevent auto resize
        # Initially hidden
        self.menu_container.place_forget()

        # ===== Scrollable Frame inside container =====
        self.menu_frame = ctk.CTkScrollableFrame(
            self.menu_container,
            fg_color=COLOR.GRAY,
            width=200,
            corner_radius=10,
            bg_color=self.master.cget("fg_color"),
        )

        self.menu_frame.pack(fill="both", expand=True)

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

    def toggle_menu(self):
        """Toggle visibility of the menu"""
        if self.menu_container.winfo_viewable():
            self.menu_container.place_forget()
        else:
            x = self.button.winfo_x() / self.button._apply_widget_scaling(1) + 20
            y = (self.button.winfo_y() + self.button.winfo_height()) / self.button._apply_widget_scaling(1) + 6
            self.menu_container.place(x=x, y=y)

    def select_option(self, code, name):
        """Select an option and close the menu"""

        self.selected_value.set(name)
        self.selected_code = code
        self.menu_container.place_forget()

        if self.on_selected_option:
            self.on_selected_option(code, name)

