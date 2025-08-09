import os
import asyncio
import logging
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatPermissions
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from fastapi import FastAPI
import uvicorn
import multiprocessing

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# FastAPI Web Server
web_app = FastAPI()

@web_app.get("/")
def health_check():
    return {"status": "active", "bot": "running"}

### CORE FUNCTIONS ###

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message with admin controls"""
    if update.effective_chat.type == "private":
        keyboard = [
            [InlineKeyboardButton("➕ Add to Group", 
             url=f"https://t.me/{context.bot.username}?startgroup=true")],
            [InlineKeyboardButton("🛡️ Admin Commands", callback_data="admin_help")]
        ]
        await update.message.reply_text(
            "🤖 <b>Supergroup Manager Bot</b>\n\n"
            "Features:\n"
            "- Auto group upgrade\n"
            "- User management\n"
            "- Spam protection\n\n"
            "Make me admin for full control!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Auto-upgrade groups to supergroups"""
    chat = update.effective_chat
    bot_id = context.bot.id
    
    if any(member.id == bot_id for member in update.message.new_chat_members):
        if chat.type == "group":
            await auto_upgrade(update, context)

async def auto_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle automatic group upgrade"""
    chat = update.effective_chat
    try:
        await update.message.reply_text(
            "🔄 <b>Automatically upgrading to supergroup...</b>\n\n"
            "Please re-add me after upgrade completes!",
            parse_mode="HTML"
        )
        await context.bot.leave_chat(chat.id)
        logger.info(f"Triggered auto-upgrade for {chat.id}")
    except Exception as e:
        logger.error(f"Upgrade failed: {e}")
        await update.message.reply_text("⚠️ Upgrade failed. Please make me admin first.")

### ADMIN COMMANDS ###

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban a user from the group"""
    if not await check_admin(update, context):
        return
    
    target = await get_target(update, context)
    if not target:
        return
    
    try:
        await context.bot.ban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id
        )
        await update.message.reply_text(
            f"🚫 Banned {target.full_name} (ID: {target.id})"
        )
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ban failed: {e}")

async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kick a user from the group"""
    if not await check_admin(update, context):
        return
    
    target = await get_target(update, context)
    if not target:
        return
    
    try:
        await context.bot.ban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id,
            until_date=60  # 1-minute ban = kick
        )
        await update.message.reply_text(
            f"👢 Kicked {target.full_name} (ID: {target.id})"
        )
    except Exception as e:
        await update.message.reply_text(f"⚠️ Kick failed: {e}")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mute a user (no sending messages)"""
    if not await check_admin(update, context):
        return
    
    target = await get_target(update, context)
    if not target:
        return
    
    try:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id,
            permissions=ChatPermissions(
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False
            )
        )
        await update.message.reply_text(
            f"🔇 Muted {target.full_name} (ID: {target.id})"
        )
    except Exception as e:
        await update.message.reply_text(f"⚠️ Mute failed: {e}")

### HELPER FUNCTIONS ###

async def check_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verify user has admin privileges"""
    user = update.effective_user
    chat = update.effective_chat
    
    try:
        member = await chat.get_member(user.id)
        if member.status not in ("administrator", "creator"):
            await update.message.reply_text("❌ You need admin rights to use this command")
            return False
        return True
    except Exception as e:
        logger.error(f"Admin check failed: {e}")
        return False

async def get_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Extract target user from command"""
    try:
        if update.message.reply_to_message:
            return update.message.reply_to_message.from_user
        
        if context.args:
            user_id = int(context.args[0])
            return await context.bot.get_chat_member(
                chat_id=update.effective_chat.id,
                user_id=user_id
            ).user
        
        await update.message.reply_text("ℹ️ Usage: /ban @username or reply to user's message")
        return None
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {e}")
        return None

### BOT SETUP ###

def run_bot():
    """Run Telegram bot with all features"""
    async def bot_main():
        app = ApplicationBuilder().token(TOKEN).build()
        
        # Core handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS,
            new_chat_members
        ))
        
        # Admin commands
        app.add_handler(CommandHandler("ban", ban_user))
        app.add_handler(CommandHandler("kick", kick_user))
        app.add_handler(CommandHandler("mute", mute_user))
        
        logger.info("🤖 Starting bot with admin controls...")
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        while True:
            await asyncio.sleep(3600)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(bot_main())
    finally:
        loop.close()

def run_web():
    """Run health check server"""
    logger.info("🌐 Starting health check server on port 8000")
    config = uvicorn.Config(
        app="IRonCore:web_app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=1
    )
    server = uvicorn.Server(config)
    server.run()

if __name__ == "__main__":
    web_process = multiprocessing.Process(target=run_web)
    web_process.start()
    
    try:
        run_bot()
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down gracefully...")
    finally:
        web_process.terminate()
        web_process.join()
