import os
import asyncio
import logging
from telegram import (
    Update,
    ChatPermissions,
    InlineKeyboardMarkup,
    InlineKeyboardButton
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
import time

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# FastAPI Web Server (for Koyeb health checks)
web_app = FastAPI()

@web_app.get("/")
def health_check():
    return {"status": "active", "bot": "running"}

### GROUP MANAGEMENT FUNCTIONS ###

async def auto_upgrade_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Automatically upgrade group to supergroup"""
    chat = update.effective_chat
    try:
        await update.message.reply_text(
            "🔄 <b>Auto-Upgrading to Supergroup...</b>\n\n"
            "Please re-add me to the new supergroup!",
            parse_mode="HTML"
        )
        await context.bot.leave_chat(chat.id)
        logger.info(f"Triggered upgrade for group {chat.id}")
    except Exception as e:
        logger.error(f"Upgrade failed: {e}")
        await update.message.reply_text("⚠️ Upgrade failed. Make me admin first.")

async def new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detect when bot is added to a group"""
    if any(member.id == context.bot.id for member in update.message.new_chat_members):
        if update.effective_chat.type == "group":
            await auto_upgrade_group(update, context)

### ADMIN COMMANDS ###

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban a user from the group"""
    if not await is_group_admin(update, context):
        return
    
    try:
        target = await get_target_user(update, context)
        await context.bot.ban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id
        )
        await update.message.reply_text(f"🚫 Banned {target.full_name}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kick a user from the group"""
    if not await is_group_admin(update, context):
        return
    
    try:
        target = await get_target_user(update, context)
        await context.bot.ban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id,
            until_date=int(time.time()) + 60  # 60-second ban = kick
        )
        await update.message.reply_text(f"👢 Kicked {target.full_name}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restrict a user from sending messages"""
    if not await is_group_admin(update, context):
        return
    
    try:
        target = await get_target_user(update, context)
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
        await update.message.reply_text(f"🔇 Muted {target.full_name}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

### HELPER FUNCTIONS ###

async def is_group_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if user is admin in group"""
    if update.effective_chat.type not in ("group", "supergroup"):
        return False
    
    try:
        member = await update.effective_chat.get_member(update.effective_user.id)
        if member.status not in ("administrator", "creator"):
            await update.message.reply_text("❌ You need admin rights for this command")
            return False
        return True
    except Exception as e:
        logger.error(f"Admin check failed: {e}")
        return False

async def get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get user to take action on"""
    try:
        # If replying to a message
        if update.message.reply_to_message:
            return update.message.reply_to_message.from_user
        
        # If using command with username/user_id
        if context.args:
            arg = context.args[0]
            if arg.startswith("@"):
                arg = arg[1:]  # Remove @ from username
            
            return (await context.bot.get_chat_member(
                chat_id=update.effective_chat.id,
                user_id=arg
            )).user
        
        await update.message.reply_text("ℹ️ Reply to a message or use: /command @username")
        return None
    except Exception as e:
        await update.message.reply_text(f"❌ Couldn't find user: {str(e)}")
        return None

### BOT SETUP ###

def run_bot():
    """Configure and start the bot"""
    async def bot_main():
        app = ApplicationBuilder().token(TOKEN).build()
        
        # Group management handlers
        app.add_handler(MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS,
            new_chat_members
        ))
        
        # Admin command handlers
        app.add_handler(CommandHandler("ban", ban_user))
        app.add_handler(CommandHandler("kick", kick_user))
        app.add_handler(CommandHandler("mute", mute_user))
        
        # Error handler
        app.add_error_handler(error_handler)
        
        logger.info("🤖 Starting Group Manager Bot...")
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        # Keep the bot running
        while True:
            await asyncio.sleep(3600)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(bot_main())
    finally:
        loop.close()

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Error: {context.error}")

def run_web_server():
    """Run health check server for Koyeb"""
    logger.info("🌐 Starting health check server on port 8000")
    uvicorn.run(
        app="IRonCore:web_app",
        host="0.0.0.0",
        port=8000,
        workers=1,
        reload=False
    )

if __name__ == "__main__":
    # Start web server in separate process
    web_process = multiprocessing.Process(target=run_web_server)
    web_process.start()
    
    # Run bot in main process
    try:
        run_bot()
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down gracefully...")
    finally:
        web_process.terminate()
        web_process.join()
