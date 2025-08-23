from customtkinter import CTkLabel, CTkTextbox, CTkFrame, CTkSwitch
from tkinter import END
import re

from widgets.frames import CustomFrame
from widgets.dropdown import CustomDropdown
from widgets.buttons import CustomButton, ImageButton
from constants import COLOR, SIZE, POS, OFFSET, FONT_SIZE, WINDOW_MARGIN, SETTINGS_WINDOW_MARGIN, WINDOW_HEIGHT, WINDOW_WIDTH, Pos, Size
from strings import STRINGS, get_default_language_code
from fonts import FONT
from helpers import open_github_issue, resource_path, open_folder
from settings_manager import Settings

INVALID_TEXTBOX_ARGS = [ "cluster", "shard", "monitor_parent_process", "token", "ownerdir", "persistent_storage_root", "ugc_directory" ]

class SettingsTooltip(CTkFrame):
    def __init__(self, master, parent, title, description):
        self._master = master
        self.parent = parent

        max_width = self.parent.winfo_reqwidth() / self.parent._apply_widget_scaling(1) - 30

        super().__init__(
            master=master,
            fg_color=COLOR.DARK_GRAY,
            border_width=0,
            corner_radius=10,
            width=max_width,
            height=0,
        )

        self.title = CTkLabel(
            master=self,
            height=0,
            text=title,
            text_color=COLOR.WHITE,
            fg_color="transparent",
            font=FONT.SETTING_TITLE,
            wraplength = max_width,
            justify="left"
        )

        self.description = CTkLabel(
            master=self,
            height=0,
            text=description,
            text_color=COLOR.WHITE_HOVER,
            fg_color="transparent",
            font=FONT.SETTING_DESC,
            wraplength = max_width,
            justify="left"
        )

        self.title.grid(
            row = 0,
            column = 0,
            padx = 10,
            sticky="nw",
        )

        self.description.grid(
            row = 1,
            column = 0,
            padx = 10,
            pady = (5, 0),
            sticky="nw",
        )

    def get_height(self):
        self.update_idletasks()

        return self.winfo_reqheight() / self.parent._apply_widget_scaling(1) + 12

    def set_position(self):
        self.parent.update_idletasks()

        self.place(
            x=self.parent.winfo_x() / self.parent._apply_widget_scaling(1),
            y=(self.parent.winfo_y() - self.winfo_reqheight()) / self.parent._apply_widget_scaling(1) - 12,
        )

class SettingsScreen():
    def __init__(self, master) -> None:
        self.corner_radius = 10
        self.master = master
        self.bind = None

        self.root = CustomFrame(
            master=master,
            color=COLOR.DARK_GRAY,
            size=SIZE.SETTINGS_PANEL,
            corner_radius=self.corner_radius,
        )

        lang_code = self.master.settings.get_setting(Settings.LANGUAGE)

        self.language_dropdown = CustomDropdown(
            master=self.root,
            options=[(code, name) for code, name in STRINGS.LANGUAGES.to_dict().items()],
            default=STRINGS.LANGUAGES[lang_code] is not None and lang_code or get_default_language_code(),
            on_selected_option=lambda code, name: self.master.settings.set_setting(Settings.LANGUAGE, code)
        )

        self.language_dropdown._tooltip = SettingsTooltip(
            master=self.root,
            parent=self.language_dropdown.button,
            title=STRINGS.SETTINGS_SCREEN.LANGUAGE.TITLE,
            description=STRINGS.SETTINGS_SCREEN.LANGUAGE.DESC,
        )

        self.language_dropdown.button.place(
            x = SETTINGS_WINDOW_MARGIN,
            y = SETTINGS_WINDOW_MARGIN + self.language_dropdown._tooltip.get_height(),
        )

        self.language_dropdown._tooltip.set_position()

        # -------------------------- #

        # self.switch = CTkSwitch(
        #     master=self.root,
        #     text="Switch Exemple",
        #     #command=command,
        #     onvalue=True,
        #     offvalue=False,
        #     fg_color=COLOR.GRAY_HOVER,
        #     progress_color=COLOR.GREEN,
        #     button_color=COLOR.WHITE,
        #     button_hover_color=COLOR.WHITE,
        #     text_color=COLOR.WHITE,
        #     font=FONT.SETTING_LONG_BUTTON,
        #     width=SIZE.LOGS_AUTO_SCROLL_SWITCH.w + 20,
        #     height=SIZE.LOGS_AUTO_SCROLL_SWITCH.h,
        # )

        # self.switch.place(
        #     x = SETTINGS_WINDOW_MARGIN,
        #     y = SETTINGS_WINDOW_MARGIN + 300,
        # )

        # -------------------------- #

        self.arguments_entry = CTkTextbox(
            master = self.root,
            corner_radius=15,
            border_color=COLOR.GRAY,
            text_color=COLOR.WHITE_HOVER,
            fg_color=COLOR.GRAY,
            font=FONT.ENTRY_ARIAL,
            border_width=0,
            height=90,
            width=350,
        )

        self.arguments_entry._textbox.configure(selectbackground=COLOR.DARK_GRAY)
        self.arguments_entry.tag_config("goodoption", foreground=COLOR.LIGHT_BLUE)
        self.arguments_entry.tag_config("badoption", foreground=COLOR.LIGHT_RED)
        self.arguments_entry.highlight_pattern = re.compile(r"([-+]\w+)")

        self.arguments_entry.bind("<KeyRelease>", self.on_arguments_textbox_key)

        self.arguments_entry.insert(END, self.master.settings.get_setting(Settings.LAUNCH_OPTIONS))
        self.on_arguments_textbox_key() # Highlight inserted text.

        self.arguments_entry._tooltip = SettingsTooltip(
            master=self.root,
            parent=self.arguments_entry,
            title=STRINGS.SETTINGS_SCREEN.LAUNCH_OPTIONS.TITLE,
            description=STRINGS.SETTINGS_SCREEN.LAUNCH_OPTIONS.DESC,
        )

        self.discord_webhook_entry = CTkTextbox(
            master = self.root,
            corner_radius=15,
            border_color=COLOR.GRAY,
            text_color=COLOR.WHITE_HOVER,
            fg_color=COLOR.GRAY,
            font=FONT.ENTRY_ARIAL,
            border_width=0,
            height=35,
            width=350,
        )

        self.discord_webhook_entry._textbox.configure(selectbackground=COLOR.DARK_GRAY)
        self.discord_webhook_entry.bind("<KeyRelease>", self.on_discord_webhook_key)

        webhook_url = self.master.settings.get_setting(Settings.DISCORD_WEBHOOK)
        if webhook_url:
            self.discord_webhook_entry.insert(END, webhook_url)

        # Calculate positions with more spacing
        webhook_section_start = SETTINGS_WINDOW_MARGIN + self.language_dropdown._tooltip.get_height() + 160
        webhook_y = webhook_section_start + 30  # Added extra space for visual separation

        self.discord_section_label = CTkLabel(
            master=self.root,
            height=30,
            text="Discord Integration",
            text_color=COLOR.WHITE,
            font=FONT.SETTING_TITLE,
        )
        
        self.discord_section_label.place(
            x=SETTINGS_WINDOW_MARGIN,
            y=webhook_section_start,
        )

        self.discord_webhook_entry.place(
            x=SETTINGS_WINDOW_MARGIN,
            y=webhook_y,
        )

        self.test_webhook_button = CustomButton(
            master=self.root,
            text="Test Webhook",
            command=self.test_webhook,
            font=FONT.SMALL_BUTTON,
            size=Size(100, 35),
            corner_radius=10,
            pos=Pos(SETTINGS_WINDOW_MARGIN, webhook_y + 60),
        )
        self.test_webhook_button.show()

        self.game_logs_switch = CTkSwitch(
            master=self.root,
            text="Show only game logs",
            command=self.on_game_logs_switch,
            onvalue=True,
            offvalue=False,
            fg_color=COLOR.GRAY_HOVER,
            progress_color=COLOR.GREEN,
            button_color=COLOR.WHITE,
            button_hover_color=COLOR.WHITE,
            text_color=COLOR.WHITE,
            font=FONT.SETTING_LONG_BUTTON,
            width=SIZE.LOGS_AUTO_SCROLL_SWITCH.w + 30,
            height=SIZE.LOGS_AUTO_SCROLL_SWITCH.h,
        )

        game_logs_only = self.master.settings.get_setting(Settings.DISCORD_GAME_LOGS_ONLY)
        self.game_logs_switch.select() if game_logs_only else self.game_logs_switch.deselect()

        self.game_logs_switch.place(
            x=SETTINGS_WINDOW_MARGIN + 170,
            y=webhook_y + 60,
        )

        self.arguments_entry = CTkTextbox(
            master = self.root,
            corner_radius=15,
            border_color=COLOR.GRAY,
            text_color=COLOR.WHITE_HOVER,
            fg_color=COLOR.GRAY,
            font=FONT.ENTRY_ARIAL,
            border_width=0,
            height=90,
            width=350,
        )

        self.arguments_entry._textbox.configure(selectbackground=COLOR.DARK_GRAY)
        self.arguments_entry.tag_config("goodoption", foreground=COLOR.LIGHT_BLUE)
        self.arguments_entry.tag_config("badoption", foreground=COLOR.LIGHT_RED)
        self.arguments_entry.highlight_pattern = re.compile(r"([-+]\w+)")

        self.arguments_entry.bind("<KeyRelease>", self.on_arguments_textbox_key)

        self.arguments_entry.insert(END, self.master.settings.get_setting(Settings.LAUNCH_OPTIONS))
        self.on_arguments_textbox_key() # Highlight inserted text.

        self.arguments_entry._tooltip = SettingsTooltip(
            master=self.root,
            parent=self.arguments_entry,
            title=STRINGS.SETTINGS_SCREEN.LAUNCH_OPTIONS.TITLE,
            description=STRINGS.SETTINGS_SCREEN.LAUNCH_OPTIONS.DESC,
        )

        self.arguments_entry.place(
            x = WINDOW_WIDTH - SETTINGS_WINDOW_MARGIN - 350,
            y = SETTINGS_WINDOW_MARGIN + self.arguments_entry._tooltip.get_height(),
        )

        self.arguments_entry._tooltip.set_position()

        # -------------------------- #

        self.button_menu = CustomFrame(
            master=self.root,
            color=COLOR.DARK_GRAY,
            size=Size(0, 0),
            corner_radius=self.corner_radius,
        )

        buttons = [
            ("APP_LOG",      "assets/file.png",      lambda: open_folder(resource_path("logs"))    ),
            ("LOCAL_FILES",  "assets/directory.png", lambda: open_folder(resource_path("savedata"))),
            ("REPORT_ISSUE", "assets/bug.png",       lambda: open_github_issue(include_applog=True)),
        ]

        for text, img, cmd in buttons:
            btn = ImageButton(
                master=self.button_menu,
                text=STRINGS.SETTINGS_SCREEN.BUTTONS[text],
                image=img,
                image_size=(SIZE.SMALL_BUTTON_LONG.h - 15, SIZE.SMALL_BUTTON_LONG.h - 15),
                command=cmd,
                font=FONT.SETTING_LONG_BUTTON,
                width=SIZE.SMALL_BUTTON_LONG.w,
                height=SIZE.SMALL_BUTTON_LONG.h,
                pos=Pos(0, 0),
                corner_radius=self.corner_radius,
            )

            btn.pack(fill="both", expand=True, pady=5, ipadx=15)

        self.button_menu.update()

        menu_width = self.button_menu.winfo_reqwidth() / self.root._apply_widget_scaling(1)

        self.button_menu.place(
            x = WINDOW_WIDTH - SETTINGS_WINDOW_MARGIN - menu_width * 1.25,
            y = SETTINGS_WINDOW_MARGIN + 250,
        )

        # -------------------------- #

        self.cancel_button = CustomButton(
            master=self.root,
            text=STRINGS.SETTINGS_SCREEN.CLOSE,
            command=self.hide,
            font=FONT.LAUNCH_BUTTON,
            size=SIZE.LOGS_CLOSE,
            corner_radius=10,
            pos=Pos(WINDOW_MARGIN, WINDOW_HEIGHT - WINDOW_MARGIN - SIZE.LOGS_CLOSE.h),
        )

        self.cancel_button.show()

        # -------------------------- #

        self.version_label = CTkLabel(
            master=self.root,
            height=0,
            anchor="se",
            text=STRINGS.VERSION_LABEL,
            text_color=COLOR.WHITE,
            font=FONT.VERSION,
        )

        self.version_label.update()

        self.version_label.place(
            x = WINDOW_WIDTH  - WINDOW_MARGIN - self.version_label.winfo_reqwidth() / self.version_label._apply_widget_scaling(1),
            y = WINDOW_HEIGHT - WINDOW_MARGIN - self.version_label.winfo_reqheight() / self.version_label._apply_widget_scaling(1),
        )

        # -------------------------- #

        self.hide()

    def show(self, *args, **kwargs):
        self._visible = True

        self.root.place(
            x=OFFSET.SETTINGS_PANEL.x,
            y=OFFSET.SETTINGS_PANEL.y,
        )

        self.root.lift()

        self.bind = self.master.bind("<Escape>", self.hide)

    def hide(self, *args, **kwargs):
        if self.master.grab_current() is not None:
            return # Not in focus...

        if self.language_dropdown.selected_code != STRINGS.current_language_code:
            restarting, _ = self.master.restart_popup.create(STRINGS.SETTINGS_SCREEN.RESTART_REQUIRED)
            
            if restarting:
                return # Don't do anything...

        self._visible = False
        self.root.place_forget()

        if self.bind:
            self.master.unbind("<Escape>", self.bind)
            self.bind = None

    def on_arguments_textbox_key(self, *args, **kwargs):
        text = self.arguments_entry.get("1.0", END)
        self.master.settings.set_setting_delayed(Settings.LAUNCH_OPTIONS, text.strip())

        # Remove existing tags
        self.arguments_entry.tag_remove("goodoption", "1.0", END)
        self.arguments_entry.tag_remove("badoption", "1.0", END)

        matches = self.arguments_entry.highlight_pattern.finditer(text)

        for match in matches:
            start, end = match.span()
            matched_word = match.group(1)[1:] # No prefix symbol.
            tag = matched_word in INVALID_TEXTBOX_ARGS and "badoption" or "goodoption"

            self.arguments_entry.tag_add(tag, f"1.0+{start}c", f"1.0+{end}c")

    def on_discord_webhook_key(self, *args, **kwargs):
        webhook_url = self.discord_webhook_entry.get("1.0", END).strip()
        self.master.settings.set_setting_delayed(Settings.DISCORD_WEBHOOK, webhook_url)
        
    def on_game_logs_switch(self):
        game_logs_only = bool(self.game_logs_switch.get())
        self.master.settings.set_setting(Settings.DISCORD_GAME_LOGS_ONLY, game_logs_only)
        
    def test_webhook(self):
        from discord_handler import DiscordWebhookHandler
        import logging
        import requests
        
        webhook_url = self.discord_webhook_entry.get("1.0", END).strip()
        logger = logging.getLogger("development")
        
        if not webhook_url:
            logger.error("Please enter a webhook URL first")
            return

        try:
            handler = DiscordWebhookHandler(webhook_url)
            test_logger = logging.getLogger("webhook_test")
            test_logger.setLevel(logging.INFO)
            test_logger.addHandler(handler)
            
            # Save the webhook URL first
            self.master.settings.set_setting(Settings.DISCORD_WEBHOOK, webhook_url)
            
            test_logger.info("🎉 Webhook test successful! Your Discord logging is configured correctly.")
            logger.info("Discord webhook tested successfully and saved")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send test message to Discord: {str(e)}")
            test_logger.removeHandler(handler)  # Clean up the test handler