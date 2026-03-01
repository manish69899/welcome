"""
Telegram Welcome/Farewell Bot
==============================
Professional bot with:
- Premium welcome cards
- Auto-delete messages
- Admin commands
- Rate limiting
- Statistics tracking
- Logging
- Keep-Alive Web Server for Render
"""

import asyncio
import json
import random
import os
import io
from datetime import datetime
from collections import defaultdict
from typing import Dict, Optional

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import BufferedInputFile, FSInputFile
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ChatType
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

# Import local modules
import config
from config import logger, is_admin, SETTINGS
from utils.image_gen import generate_welcome_card
from keep_alive import start_web_server

# ==================== BOT INITIALIZATION ====================
bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML,
        link_preview_is_disabled=True
    )
)
dp = Dispatcher()

# ==================== DATA STRUCTURES ====================
# Load dialogues
DIALOGUES_PATH = os.path.join(os.path.dirname(__file__), "data", "dialogues.json")
try:
    with open(DIALOGUES_PATH, "r", encoding="utf-8") as f:
        DIALOGUES = json.load(f)
    logger.info("Dialogues loaded successfully")
except Exception as e:
    logger.error(f"Failed to load dialogues: {e}")
    DIALOGUES = {
        "welcome_group": ["Welcome to the group! 🎉"],
        "farewell_group": ["Goodbye! 👋"],
        "welcome_channel": ["Welcome to the channel! 🎉"],
        "farewell_channel": ["Goodbye! 👋"],
        "admin_messages": {}
    }

# Rate limiting
user_cooldowns: Dict[int, datetime] = defaultdict(lambda: datetime.min)

# Statistics
class BotStats:
    """Simple in-memory statistics tracker."""
    def __init__(self):
        self.total_joins = 0
        self.total_leaves = 0
        self.messages_sent = 0
        self.welcome_cards_generated = 0
        self.start_time = datetime.now()
        self.group_stats: Dict[int, Dict] = defaultdict(lambda: {"joins": 0, "leaves": 0})
    
    def record_join(self, chat_id: int):
        self.total_joins += 1
        self.group_stats[chat_id]["joins"] += 1
    
    def record_leave(self, chat_id: int):
        self.total_leaves += 1
        self.group_stats[chat_id]["leaves"] += 1
    
    def record_message(self):
        self.messages_sent += 1
    
    def record_welcome_card(self):
        self.welcome_cards_generated += 1
    
    def get_uptime(self) -> str:
        delta = datetime.now() - self.start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}h {minutes}m {seconds}s"

stats = BotStats()


# ==================== RATE LIMITING ====================
def check_rate_limit(user_id: int, cooldown_seconds: int = 5) -> bool:
    """Check if user is rate limited."""
    now = datetime.now()
    last_action = user_cooldowns[user_id]
    
    if (now - last_action).total_seconds() < cooldown_seconds:
        return False
    
    user_cooldowns[user_id] = now
    return True


# ==================== HELPER FUNCTIONS ====================
async def delete_message_later(message: types.Message, delay: int) -> None:
    """Delete message after specified delay."""
    if delay <= 0:
        logger.debug(f"Auto-delete is set to {delay}s, skipping deletion.")
        return
        
    await asyncio.sleep(delay)
    try:
        await message.delete()
        logger.debug(f"Message {message.message_id} deleted after {delay}s")
    except TelegramBadRequest:
        logger.debug(f"Message {message.message_id} already deleted")
    except Exception as e:
        logger.warning(f"Failed to delete message: {e}")


async def get_user_profile_pic_bytes(user_id: int) -> Optional[bytes]:
    """Get user's profile picture as bytes."""
    try:
        photos = await bot.get_user_profile_photos(user_id, limit=1)
        if photos.total_count > 0:
            file_id = photos.photos[0][-1].file_id
            file = await bot.get_file(file_id)
            # Download directly as bytes (no token exposure!)
            pic_bytes = await bot.download_file(file.file_path)
            return pic_bytes.read()
    except Exception as e:
        logger.debug(f"Could not get profile picture for {user_id}: {e}")
    return None


def format_welcome_caption(
    user: types.User,
    dialogue: str,
    join_date: str,
    chat_title: str
) -> str:
    """Format the premium VIP welcome message caption."""
    
    # VIP Tagging Logic (Notification ensure karega)
    if user.username:
        mention = f"<a href='tg://user?id={user.id}'>@{user.username}</a>"
    else:
        mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
    
    return (
        f"✨ <b>W E L C O M E</b> ✨\n\n"
        f"Aaiye {mention}, <b>{chat_title}</b> ki shandaar duniya mein aapka swagat hai! 🎉🔥\n\n"
        f"<b>╭━━━ ⟡ I N F O ⟡ ━━━╮</b>\n"
        f"<b>┣ 👤 Name :</b> {user.full_name}\n"
        f"<b>┣ 💎 User :</b> {mention}\n"
        f"<b>┣ 🆔 ID   :</b> <code>{user.id}</code>\n"
        f"<b>┣ 📅 Date :</b> {join_date}\n"
        f"<b>╰━━━━━━━━━━━━━━━━━━╯</b>\n\n"
        f"<blockquote expandable>"
        f"💬 <i>\"{dialogue}\"</i>\n\n"
        f"⚠️ <b>Note:</b> Group ke pinned messages zaroor padhein aur rules follow karein. Enjoy your stay! 🥂"
        f"</blockquote>"
    )

def format_farewell_caption(
    user: types.User,
    dialogue: str
) -> str:
    """Format the farewell message."""
    return (
        f"<blockquote>"
        f"👋 <b><a href='tg://user?id={user.id}'>{user.full_name}</a></b> left the chat.\n\n"
        f"<i>{dialogue}</i>"
        f"</blockquote>"
    )


# ==================== SERVICE MESSAGE DELETER ====================
@dp.message(F.new_chat_members | F.left_chat_member)
async def delete_system_messages(message: types.Message):
    """Instantly deletes Telegram's default 'User joined' and 'User left' messages."""
    try:
        await message.delete()
        logger.debug("Deleted a system joined/left message.")
    except Exception as e:
        logger.warning(f"Failed to delete system message. (Bot might not be admin): {e}")


# ==================== START & HELP COMMANDS ====================
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """Handle /start command."""
    if message.chat.type != ChatType.PRIVATE:
        return
    
    welcome_text = (
        f"👋 <b>Hello, {message.from_user.first_name}!</b>\n\n"
        f"🤖 <b>I'm a Premium Welcome Bot</b>\n\n"
        f"<b>✨ Features:</b>\n"
        f"• Premium anime-style welcome cards\n"
        f"• Auto-deletes 'User joined/left' service messages\n"
        f"• Custom farewell messages\n"
        f"• Auto-delete messages\n"
        f"• Admin controls\n\n"
        f"<b>📋 Commands:</b>\n"
        f"• /start - Show this message\n"
        f"• /help - Get help\n"
        f"• /stats - Bot statistics (admin)\n"
        f"• /health - Bot health check\n"
        f"• /set_group_timer - Set group welcome timer (admin)\n"
        f"• /set_channel_timer - Set channel welcome timer (admin)\n\n"
        f"📌 <b>Add me to your group/channel and make me admin to get started!</b>"
    )
    await message.reply(welcome_text)
    stats.record_message()


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Handle /help command."""
    help_text = (
        "<b>📚 Bot Help Guide</b>\n\n"
        "<b>🔧 Setup Instructions:</b>\n"
        "1. Add bot to your group/channel\n"
        "2. Give bot admin rights (to delete messages)\n"
        "3. That's it! Bot will welcome new members\n\n"
        "<b>⚙️ Admin Commands:</b>\n"
        "• <code>/set_group_timer [seconds]</code> - Set auto-delete timer for groups\n"
        "• <code>/set_channel_timer [seconds]</code> - Set auto-delete timer for channels\n"
        "• <code>/stats</code> - View bot statistics\n"
        "• <code>/health</code> - Check bot health\n\n"
        "<b>💡 Tips:</b>\n"
        "• Default group timer: 900 seconds (15 mins)\n"
        "• Default channel timer: 120 seconds (2 mins)\n"
        "• Welcome cards are auto-generated\n\n"
        "<b>❓ Need more help?</b>\n"
        "Contact the bot administrator."
    )
    await message.reply(help_text)
    stats.record_message()


# ==================== ADMIN COMMANDS ====================
@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Show bot statistics (admin only)."""
    if not is_admin(message.from_user.id):
        await message.reply(DIALOGUES.get("admin_messages", {}).get("no_permission", "❌ Admin only!"))
        return
    
    uptime = stats.get_uptime()
    stats_text = (
        f"📊 <b>{DIALOGUES.get('admin_messages', {}).get('stats_header', 'Bot Statistics')}</b>\n\n"
        f"⏱️ <b>Uptime:</b> {uptime}\n"
        f"👥 <b>Total Joins:</b> {stats.total_joins}\n"
        f"👋 <b>Total Leaves:</b> {stats.total_leaves}\n"
        f"💬 <b>Messages Sent:</b> {stats.messages_sent}\n"
        f"🎨 <b>Cards Generated:</b> {stats.welcome_cards_generated}\n\n"
        f"⚙️ <b>Current Settings:</b>\n"
        f"• Group Timer: {SETTINGS.get('group_auto_delete_sec')}s\n"
        f"• Channel Timer: {SETTINGS.get('channel_auto_delete_sec')}s\n"
        f"• Welcome Enabled: {SETTINGS.get('welcome_enabled')}\n"
        f"• Farewell Enabled: {SETTINGS.get('farewell_enabled')}"
    )
    await message.reply(stats_text)
    stats.record_message()


@dp.message(Command("health"))
async def cmd_health(message: types.Message):
    """Check bot health status."""
    health_text = (
        f"🩺 <b>{DIALOGUES.get('admin_messages', {}).get('health_header', 'Bot Health Status')}</b>\n\n"
        f"✅ <b>Status:</b> Online & Healthy\n"
        f"⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"🐍 <b>Python:</b> Async Mode\n"
        f"🤖 <b>Library:</b> aiogram 3.x\n"
        f"📸 <b>Image Engine:</b> PIL/Pillow\n\n"
        f"✨ <b>All systems operational!</b>"
    )
    await message.reply(health_text)
    stats.record_message()


@dp.message(Command("set_group_timer"))
async def cmd_set_group_timer(message: types.Message):
    """Set group welcome auto-delete timer (admin only)."""
    if not is_admin(message.from_user.id):
        await message.reply(DIALOGUES.get("admin_messages", {}).get("no_permission", "❌ Admin only!"))
        return
    
    try:
        args = message.text.split()
        if len(args) < 2:
            raise ValueError("Missing argument")
        
        time_sec = int(args[1])
        if time_sec < 0 or time_sec > 86400:  # Max 24 hours
            await message.reply("⚠️ Timer must be between 0 and 86400 seconds (24 hours)")
            return
        
        SETTINGS.set("group_auto_delete_sec", time_sec)
        await message.reply(
            f"✅ Group auto-delete timer set to <b>{time_sec} seconds</b>.\n"
            f"{'⚠️ Note: Timer disabled (0 seconds)' if time_sec == 0 else ''}"
        )
        logger.info(f"Group timer set to {time_sec}s by {message.from_user.id}")
        
    except (IndexError, ValueError):
        await message.reply(
            f"⚠️ {DIALOGUES.get('admin_messages', {}).get('invalid_format', 'Invalid format!')}\n\n"
            f"📝 <b>Usage:</b> <code>/set_group_timer [seconds]</code>\n"
            f"📌 <b>Example:</b> <code>/set_group_timer 900</code>"
        )


@dp.message(Command("set_channel_timer"))
async def cmd_set_channel_timer(message: types.Message):
    """Set channel welcome auto-delete timer (admin only)."""
    if not is_admin(message.from_user.id):
        await message.reply(DIALOGUES.get("admin_messages", {}).get("no_permission", "❌ Admin only!"))
        return
    
    try:
        args = message.text.split()
        if len(args) < 2:
            raise ValueError("Missing argument")
        
        time_sec = int(args[1])
        if time_sec < 0 or time_sec > 86400:
            await message.reply("⚠️ Timer must be between 0 and 86400 seconds (24 hours)")
            return
        
        SETTINGS.set("channel_auto_delete_sec", time_sec)
        await message.reply(
            f"✅ Channel auto-delete timer set to <b>{time_sec} seconds</b>.\n"
            f"{'⚠️ Note: Timer disabled (0 seconds)' if time_sec == 0 else ''}"
        )
        logger.info(f"Channel timer set to {time_sec}s by {message.from_user.id}")
        
    except (IndexError, ValueError):
        await message.reply(
            f"⚠️ {DIALOGUES.get('admin_messages', {}).get('invalid_format', 'Invalid format!')}\n\n"
            f"📝 <b>Usage:</b> <code>/set_channel_timer [seconds]</code>\n"
            f"📌 <b>Example:</b> <code>/set_channel_timer 120</code>"
        )


@dp.message(Command("toggle_welcome"))
async def cmd_toggle_welcome(message: types.Message):
    """Toggle welcome messages (admin only)."""
    if not is_admin(message.from_user.id):
        await message.reply(DIALOGUES.get("admin_messages", {}).get("no_permission", "❌ Admin only!"))
        return
    
    current = SETTINGS.get("welcome_enabled", True)
    SETTINGS.set("welcome_enabled", not current)
    
    status = "✅ Enabled" if not current else "❌ Disabled"
    await message.reply(f"🔄 Welcome messages: {status}")
    logger.info(f"Welcome toggled to {not current} by {message.from_user.id}")


@dp.message(Command("toggle_farewell"))
async def cmd_toggle_farewell(message: types.Message):
    """Toggle farewell messages (admin only)."""
    if not is_admin(message.from_user.id):
        await message.reply(DIALOGUES.get("admin_messages", {}).get("no_permission", "❌ Admin only!"))
        return
    
    current = SETTINGS.get("farewell_enabled", True)
    SETTINGS.set("farewell_enabled", not current)
    
    status = "✅ Enabled" if not current else "❌ Disabled"
    await message.reply(f"🔄 Farewell messages: {status}")
    logger.info(f"Farewell toggled to {not current} by {message.from_user.id}")


# ==================== WELCOME HANDLER ====================
@dp.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_user_join(event: types.ChatMemberUpdated):
    """Handle user joining group/channel."""
    if not SETTINGS.get("welcome_enabled", True):
        return
    
    new_user = event.new_chat_member.user
    chat = event.chat
    
    # Rate limiting check
    if not check_rate_limit(new_user.id, SETTINGS.get("rate_limit_seconds", 5)):
        logger.debug(f"Rate limited user: {new_user.id}")
        return
    
    stats.record_join(chat.id)
    
    # === CHANNEL WELCOME ===
    if chat.type == ChatType.CHANNEL:
        dialogue = random.choice(DIALOGUES["welcome_channel"])
        text = (
            f"<b>Welcome to {chat.title}!</b>\n\n"
            f"Hey <a href='tg://user?id={new_user.id}'>{new_user.full_name}</a>, {dialogue}"
        )
        
        try:
            msg = await bot.send_message(chat.id, text)
            stats.record_message()
            
            delay = SETTINGS.get("channel_auto_delete_sec", 120)
            if delay > 0:
                asyncio.create_task(delete_message_later(msg, delay))
                
            logger.info(f"Channel welcome sent to {new_user.id} in {chat.id}")
            
        except TelegramForbiddenError:
            logger.error(f"Bot not admin in channel {chat.id}")
        except Exception as e:
            logger.error(f"Error sending channel welcome: {e}")
        return
    
    # === GROUP WELCOME ===
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        dialogue = random.choice(DIALOGUES["welcome_group"])
        join_date = datetime.now().strftime("%d %B %Y")
        
        try:
            # Get profile picture
            pfp_bytes = await get_user_profile_pic_bytes(new_user.id)
            
            # Generate welcome card
            image_bytes = await generate_welcome_card(
                user_pic_bytes=pfp_bytes,
                user_name=new_user.first_name or "User",
                subtitle="WELCOME",
                theme='gold'
            )
            stats.record_welcome_card()
            
            # Prepare photo
            photo = BufferedInputFile(image_bytes.getvalue(), filename="welcome.jpg")
            
            # Format caption
            caption = format_welcome_caption(new_user, dialogue, join_date)
            
            # Send welcome message
            msg = await bot.send_photo(
                chat_id=chat.id,
                photo=photo,
                caption=caption
            )
            stats.record_message()
            
            # Schedule auto-delete
            delay = SETTINGS.get("group_auto_delete_sec", 900)
            if delay > 0:
                asyncio.create_task(delete_message_later(msg, delay))
            
            logger.info(f"Group welcome sent to {new_user.id} in {chat.id}")
            
        except TelegramForbiddenError:
            logger.error(f"Bot not admin in group {chat.id}")
        except Exception as e:
            logger.error(f"Error sending group welcome: {e}")
            # Fallback: Send text-only welcome
            try:
                text = f"👋 Welcome <a href='tg://user?id={new_user.id}'>{new_user.full_name}</a>!\n\n{dialogue}"
                msg = await bot.send_message(chat.id, text)
                stats.record_message()
                
                delay = SETTINGS.get("group_auto_delete_sec", 900)
                if delay > 0:
                    asyncio.create_task(delete_message_later(msg, delay))
            except Exception as e2:
                logger.error(f"Fallback welcome also failed: {e2}")


# ==================== FAREWELL HANDLER ====================
@dp.chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def on_user_leave(event: types.ChatMemberUpdated):
    """Handle user leaving group/channel."""
    if not SETTINGS.get("farewell_enabled", True):
        return
    
    user = event.old_chat_member.user
    chat = event.chat
    
    stats.record_leave(chat.id)
    
    # === CHANNEL FAREWELL ===
    if chat.type == ChatType.CHANNEL:
        dialogue = random.choice(DIALOGUES["farewell_channel"])
        text = f"Bye <a href='tg://user?id={user.id}'>{user.full_name}</a>! {dialogue}"
        
        try:
            msg = await bot.send_message(chat.id, text)
            stats.record_message()
            
            delay = SETTINGS.get("channel_auto_delete_sec", 120)
            if delay > 0:
                asyncio.create_task(delete_message_later(msg, delay))
                
            logger.info(f"Channel farewell sent for {user.id} in {chat.id}")
            
        except Exception as e:
            logger.error(f"Error sending channel farewell: {e}")
        return
    
    # === GROUP FAREWELL ===
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        dialogue = random.choice(DIALOGUES["farewell_group"])
        text = format_farewell_caption(user, dialogue)
        
        try:
            msg = await bot.send_message(chat.id, text)
            stats.record_message()
            
            delay = SETTINGS.get("group_auto_delete_sec", 900)
            if delay > 0:
                asyncio.create_task(delete_message_later(msg, delay))
            
            logger.info(f"Group farewell sent for {user.id} in {chat.id}")
            
        except Exception as e:
            logger.error(f"Error sending group farewell: {e}")


# ==================== ERROR HANDLER ====================
@dp.error()
async def error_handler(event: types.ErrorEvent):
    """Global error handler."""
    logger.error(f"Error: {event.exception}")
    
    # Try to notify if possible
    if event.update and hasattr(event.update, 'message') and event.update.message:
        try:
            await event.update.message.reply(
                "⚠️ An error occurred. Please try again later."
            )
        except:
            pass
    
    return True


# ==================== MAIN ENTRY POINT ====================
async def main():
    """Main entry point for the bot."""
    logger.info("=" * 50)
    logger.info("🤖 Telegram Welcome Bot Starting...")
    logger.info("=" * 50)
    
    # Verify configuration
    if not config.BOT_TOKEN:
        logger.critical("BOT_TOKEN not found in environment!")
        return
    
    logger.info(f"✅ Bot Token: {'*' * 10}...{config.BOT_TOKEN[-5:]}")
    logger.info(f"✅ Admin ID: {config.ADMIN_ID}")
    logger.info(f"✅ Settings loaded: {len(SETTINGS.get_all())} items")
    
    # 🌟 Sabse pehle Web Server ko start karo (For Render Keep-Alive)
    logger.info("🌐 Starting Web Server for Keep-Alive in Background...")
    # Fix applied here: Use create_task so it doesn't block the rest of the code!
    asyncio.create_task(start_web_server())
    
    # Delete webhook and clear pending updates
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook deleted, pending updates cleared")
    except Exception as e:
        logger.warning(f"Could not delete webhook: {e}")
    
    # Start polling
    logger.info("🚀 Bot is now running! Press Ctrl+C to stop.")
    logger.info("=" * 50)
    
    try:
        await dp.start_polling(
            bot,
            allowed_updates=[
                "message",
                "chat_member",
                "my_chat_member"
            ]
        )
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Bot crashed: {e}")
    finally:
        await bot.session.close()
        logger.info("Bot session closed")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutdown complete")