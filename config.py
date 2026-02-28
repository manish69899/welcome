"""
Telegram Bot Configuration Module
==================================
Professional configuration management with:
- Environment variable loading
- Settings persistence
- Error handling
- Logging support
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from dataclasses import dataclass

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== PATHS ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "data", "settings.json")
DIALOGUES_FILE = os.path.join(BASE_DIR, "data", "dialogues.json")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")


# ==================== CONFIGURATION CLASS ====================
@dataclass
class BotConfig:
    """Bot configuration container with validation."""
    bot_token: str
    admin_id: int
    owner_id: int = 0  # Optional owner ID for extra permissions
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.bot_token:
            raise ValueError("BOT_TOKEN is required! Please set it in .env file")
        if self.admin_id == 0:
            logger.warning("ADMIN_ID is 0. Admin commands will not work properly!")


# ==================== SETTINGS MANAGEMENT ====================
class SettingsManager:
    """
    Professional settings manager with:
    - JSON persistence
    - Default values
    - Type validation
    - Auto-save functionality
    """
    
    # Default settings
    DEFAULT_SETTINGS: Dict[str, Any] = {
        "group_auto_delete_sec": 60,
        "channel_auto_delete_sec": 15,
        "welcome_enabled": True,
        "farewell_enabled": True,
        "image_welcome_enabled": True,
        "max_name_length": 14,
        "rate_limit_seconds": 5,
        "log_events": True,
        "stats_enabled": True
    }
    
    def __init__(self, settings_file: str = SETTINGS_FILE):
        self.settings_file = settings_file
        self._settings: Dict[str, Any] = {}
        self._load()
    
    def _load(self) -> None:
        """Load settings from JSON file."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    self._settings = json.load(f)
                logger.info(f"Settings loaded from {self.settings_file}")
            else:
                self._settings = self.DEFAULT_SETTINGS.copy()
                self._save()
                logger.info("Created new settings file with defaults")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in settings file: {e}")
            self._settings = self.DEFAULT_SETTINGS.copy()
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            self._settings = self.DEFAULT_SETTINGS.copy()
    
    def _save(self) -> None:
        """Save settings to JSON file."""
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=4, ensure_ascii=False)
            logger.debug("Settings saved successfully")
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value with fallback to default."""
        return self._settings.get(key, self.DEFAULT_SETTINGS.get(key, default))
    
    def set(self, key: str, value: Any, auto_save: bool = True) -> None:
        """Set a setting value and optionally save."""
        self._settings[key] = value
        if auto_save:
            self._save()
        logger.info(f"Setting '{key}' updated to: {value}")
    
    def get_all(self) -> Dict[str, Any]:
        """Get all settings."""
        return self._settings.copy()
    
    def update(self, new_settings: Dict[str, Any], auto_save: bool = True) -> None:
        """Update multiple settings at once."""
        self._settings.update(new_settings)
        if auto_save:
            self._save()
        logger.info(f"Updated {len(new_settings)} settings")
    
    def reset(self) -> None:
        """Reset all settings to defaults."""
        self._settings = self.DEFAULT_SETTINGS.copy()
        self._save()
        logger.info("Settings reset to defaults")


# ==================== GLOBAL INSTANCES ====================
def _get_config() -> BotConfig:
    """Create and return bot configuration."""
    return BotConfig(
        bot_token=os.getenv("BOT_TOKEN", ""),
        admin_id=int(os.getenv("ADMIN_ID", "0")),
        owner_id=int(os.getenv("OWNER_ID", "0"))
    )


# Initialize config
try:
    CONFIG = _get_config()
    logger.info("Bot configuration loaded successfully")
except ValueError as e:
    logger.critical(f"Configuration error: {e}")
    raise

# Initialize settings manager
SETTINGS = SettingsManager()

# Convenience accessors
BOT_TOKEN = CONFIG.bot_token
ADMIN_ID = CONFIG.admin_id
OWNER_ID = CONFIG.owner_id


# ==================== HELPER FUNCTIONS ====================
def get_settings() -> Dict[str, Any]:
    """Get current settings dictionary."""
    return SETTINGS.get_all()


def update_settings(new_settings: Dict[str, Any]) -> None:
    """Update settings with new values."""
    SETTINGS.update(new_settings)


def is_admin(user_id: int) -> bool:
    """Check if user is admin or owner."""
    return user_id in [ADMIN_ID, OWNER_ID] if OWNER_ID else user_id == ADMIN_ID


def get_asset_path(filename: str) -> str:
    """Get full path to an asset file."""
    return os.path.join(ASSETS_DIR, filename)


# ==================== EXPORTS ====================
__all__ = [
    'BOT_TOKEN',
    'ADMIN_ID', 
    'OWNER_ID',
    'CONFIG',
    'SETTINGS',
    'get_settings',
    'update_settings',
    'is_admin',
    'get_asset_path',
    'SettingsManager',
    'BotConfig',
    'logger'
]
