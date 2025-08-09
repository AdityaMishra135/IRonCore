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

### GROUP-SPECIFIC FUNCTIONS ###

async def group_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verify command is used in group chat"""
    if update.effective_chat.type not in ("group", "supergroup"):
        await update.message.reply_text("❌ This command only works in group chats")
        return False
    return True

async def auto_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            await auto_upgrade(update, context)

### ADMIN COMMANDS (GROUP ONLY) ###

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban user (group only)"""
    if not await group_check(update, context) or not await check_admin(update, context):
        return
    
    target = await get_target(update, context)
    if not target:
        return
    
    try:
        await context.bot.ban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id
        )
        await update.message.reply_text(f"🚫 Banned {target.full_name}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {e}")

async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kick user (group only)"""
    if not await group_check(update, context) or not await check_admin(update, context):
        return
    
    target = await get_target(update, context)
    if not target:
        return
    
    try:
        await context.bot.ban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id,
            until_date=int(time.time()) + 60  # 60-second ban = kick
        )
        await update.message.reply_text(f"👢 Kicked {target.full_name}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {e}")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mute user (group only)"""
    if not await group_check(update, context) or not await check_admin(update, context):
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
        await update.message.reply_text(f"🔇 Muted {target.full_name}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {e}")

### HELPER FUNCTIONS ###

async def check_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verify user is admin"""
    try:
        member = await update.effective_chat.get_member(update.effective_user.id)
        return member.status in ("administrator", "creator")
    except Exception as e:
        logger.error(f"Admin check failed: {e}")
        return False

async def get_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get target user from command"""
    try:
        if update.message.reply_to_message:
            return update.message.reply_to_message.from_user
        
        if context.args:
            if context.args[0].startswith("@"):
                user = await context.bot.get_chat_member(
                    chat_id=update.effective_chat.id,
                    user_id=context.args[0][1:]
                )
                return user.user
            return (await context.bot.get_chat_member(
                chat_id=update.effective_chat.id,
                user_id=int(context.args[0])
            ).user
        
        await update.message.reply_text("ℹ️ Reply to user or use /command @username")
        return None
    except Exception as e:
        await update.message.reply_text(f"❌ Invalid target: {e}")
        return None

### BOT SETUP ###

def run_bot():
    """Configure and start bot"""
    async def bot_main():
        app = ApplicationBuilder().token(TOKEN).build()
        
        # Group management
        app.add_handler(MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS,
            new_chat_members
        ))
        
        # Admin commands
        app.add_handler(CommandHandler("ban", ban_user))
        app.add_handler(CommandHandler("kick", kick_user))
        app.add_handler(CommandHandler("mute", mute_user))
        
        logger.info("🤖 Starting group management bot...")
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
    """Health check server"""
    logger.info("🌐 Starting health check server")
    uvicorn.run(
        app="IRonCore:web_app",
        host="0.0.0.0",
        port=8000,
        workers=1,
        reload=False
    )

if __name__ == "__main__":
    web_process = multiprocessing.Process(target=run_web)
    web_process.start()
    
    try:
        run_bot()
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down...")
    finally:
        web_process.terminate()
        web_process.join()
