import os
import asyncio
import logging
import time
from datetime import datetime
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

### CORE GROUP FUNCTIONS ###

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
    
    target = await get_target_user(update, context)
    if not target:
        return
    
    try:
        await context.bot.ban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id
        )
        await update.message.reply_text(
            f"🚫 <b>Banned:</b> {target.mention_html()} (ID: <code>{target.id}</code>)",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ <b>Ban Failed</b>\n\n"
            f"Error: {str(e)}\n\n"
            f"Possible reasons:\n"
            f"- I need admin permissions\n"
            f"- Target is admin/owner\n"
            f"- User already left",
            parse_mode="HTML"
        )

async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kick a user from the group"""
    if not await is_group_admin(update, context):
        return
    
    target = await get_target_user(update, context)
    if not target:
        return
    
    try:
        await context.bot.ban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id,
            until_date=int(time.time()) + 60  # 60-second ban = kick
        )
        await update.message.reply_text(
            f"👢 <b>Kicked:</b> {target.mention_html()} (ID: <code>{target.id}</code>)",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ <b>Kick Failed</b>\n\n"
            f"Error: {str(e)}\n\n"
            f"Possible reasons:\n"
            f"- I need admin permissions\n"
            f"- Target is admin/owner\n"
            f"- User already left",
            parse_mode="HTML"
        )

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restrict a user from sending messages"""
    if not await is_group_admin(update, context):
        return
    
    target = await get_target_user(update, context)
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
            f"🔇 <b>Muted:</b> {target.mention_html()} (ID: <code>{target.id}</code>)",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ <b>Mute Failed</b>\n\n"
            f"Error: {str(e)}\n\n"
            f"Possible reasons:\n"
            f"- I need admin permissions\n"
            f"- Target is admin/owner",
            parse_mode="HTML"
        )

async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed information about a user (including owners)"""
    target = await get_target_user(update, context)
    if not target:
        return
    
    try:
        member = await context.bot.get_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id
        )
        
        # Handle owner case (no joined_date)
        join_date = (
            member.joined_date.strftime("%Y-%m-%d %H:%M:%S") 
            if hasattr(member, 'joined_date') and member.joined_date 
            else "Owner/Creator"
        )
        
        # Get last online if available
        last_online = (
            member.user.last_online_date.strftime("%Y-%m-%d %H:%M:%S") 
            if hasattr(member.user, 'last_online_date') and member.user.last_online_date
            else "Unknown"
        )
        
        message = (
            f"👤 <b>User Information</b>\n\n"
            f"🆔 ID: <code>{target.id}</code>\n"
            f"📛 Name: {target.mention_html()}\n"
            f"📅 Joined: {join_date}\n"
            f"⏱️ Last Online: {last_online}\n"
            f"👑 Status: {member.status}\n"
            f"🤖 Is Bot: {'Yes' if target.is_bot else 'No'}\n"
            f"🔗 Username: @{target.username if target.username else 'N/A'}\n"
            f"📝 Bio: {target.bio if hasattr(target, 'bio') else 'N/A'}"
        )
        
        await update.message.reply_text(message, parse_mode="HTML")
        
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ <b>Info Failed</b>\n\n"
            f"Error: {str(e)}",
            parse_mode="HTML"
        )

### HELPER FUNCTIONS ###

async def is_group_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if user is admin in group"""
    if update.effective_chat.type not in ("group", "supergroup"):
        await update.message.reply_text("❌ This command only works in groups")
        return False
    
    try:
        member = await update.effective_chat.get_member(update.effective_user.id)
        if member.status not in ("administrator", "creator"):
            await update.message.reply_text("❌ You need admin rights for this command")
            return False
        return True
    except Exception as e:
        logger.error(f"Admin check failed: {e}")
        await update.message.reply_text("⚠️ Error checking admin status")
        return False

async def get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Robust user targeting with exact username matching"""
    try:
        # Case 1: Command with reply
        if update.message.reply_to_message:
            return update.message.reply_to_message.from_user

        # Case 2: Command with argument
        if not context.args:
            await update.message.reply_text(
                "🔍 <b>How to target users:</b>\n\n"
                "1. Reply to user's message with /command\n"
                "2. /command @username (case sensitive)\n"
                "3. /command 123456789 (user ID)\n\n"
                "<i>Note: Usernames must match exactly</i>",
                parse_mode="HTML"
            )
            return None

        target = context.args[0].strip()
        
        # Exact username matching (case sensitive)
        if target.startswith('@'):
            target = target[1:]  # Remove @
            async for member in context.bot.get_chat_members(update.effective_chat.id):
                if member.user.username and member.user.username == target:
                    return member.user
        
        # Numeric ID fallback
        if target.isdigit():
            try:
                member = await context.bot.get_chat_member(
                    chat_id=update.effective_chat.id,
                    user_id=int(target)
                )
                return member.user
            except Exception:
                pass
        
        # Final attempt with ID string match
        async for member in context.bot.get_chat_members(update.effective_chat.id):
            if str(member.user.id) == target:
                return member.user

        await update.message.reply_text(
            f"❌ <b>User not found</b>\n\n"
            f"No exact match for '@{target}'.\n"
            f"Try using:\n"
            f"1. Their exact @username\n"
            f"2. Their numeric ID\n"
            f"3. Reply to their message",
            parse_mode="HTML"
        )
        return None

    except Exception as e:
        logger.error(f"Target error: {str(e)}", exc_info=True)
        await update.message.reply_text(
            "⚠️ <b>Targeting Error</b>\n\n"
            "Please try:\n"
            "1. Replying to the user's message\n"
            "2. Using their exact @username\n"
            "3. Using their numeric ID",
            parse_mode="HTML"
        )
        return None

### BOT SETUP ###

def run_bot():
    """Configure and start the bot"""
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
        app.add_handler(CommandHandler("info", user_info))
        
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
    logger.error(f"Error: {context.error}", exc_info=True)

def run_web_server():
    """Run health check server"""
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
