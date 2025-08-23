import logging
import requests
import json
from datetime import datetime

class DiscordWebhookHandler(logging.Handler):
    def __init__(self, webhook_url, app_name="Vox Launcher", game_logs_only=False):
        super().__init__()
        self.webhook_url = webhook_url
        self.app_name = app_name
        self.game_logs_only = game_logs_only
        
    def is_game_log(self, record):
        """Check if this is a game-related log message"""
        game_keywords = [
            "shard", "server", "cluster", "world", "save", "rollback",
            "Starting server", "Shutting down", "Connected to", "Player",
            "Server is now"
        ]
        return any(keyword.lower() in record.getMessage().lower() for keyword in game_keywords)

    def emit(self, record):
        if not self.webhook_url:
            return
            
        if self.game_logs_only and not self.is_game_log(record):
            return

        try:
            log_entry = self.format(record)
            
            # Create Discord embed
            embed = {
                "title": f"{self.app_name} - {record.levelname}",
                "description": f"```\n{log_entry}\n```",
                "color": self._get_level_color(record.levelname),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send to Discord
            requests.post(
                self.webhook_url,
                json={"embeds": [embed]},
                headers={"Content-Type": "application/json"},
                timeout=5
            )
        except Exception:
            self.handleError(record)

    def _get_level_color(self, level_name):
        colors = {
            'DEBUG': 0x7289DA,    # Discord Blurple
            'INFO': 0x2ECC71,     # Green
            'WARNING': 0xF1C40F,  # Yellow
            'ERROR': 0xE74C3C,    # Red
            'CRITICAL': 0x992D22  # Dark Red
        }
        return colors.get(level_name, 0x7289DA)
