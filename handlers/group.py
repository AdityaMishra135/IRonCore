import os
import logging
from telegram import Update
from datetime import datetime
from telegram.ext import ContextTypes, MessageHandler, filters, CommandHandler
from database.database import (
    store_join_date, 
    get_join_date,
    set_welcome_message,
    get_welcome_message,
    set_goodbye_message,
    get_goodbye_message
)


# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_WELCOME_MSG = "👋 Welcome {mention} to {chat_title}!"
DEFAULT_GOODBYE_MSG = "👋 {mention} has left {chat_title}!"
user_join_dates = {}  # Format: {chat_id: {user_id: join_timestamp}}

async def new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new members including bot itself"""
    if any(member.id == context.bot.id for member in update.message.new_chat_members):
        if update.effective_chat.type == "group":
            await auto_upgrade_group(update, context)
        return
    
    # Store join dates in database
    for member in update.message.new_chat_members:
        store_join_date(update.effective_chat.id, member.id)
    
    await send_welcome_message(update, context)

def get_user_join_date(chat_id: int, user_id: int) -> datetime:
    """Get stored join date for a user from database"""
    return get_join_date(chat_id, user_id)  # Changed to use database



async def send_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message for new members"""
    try:
        chat_id = update.effective_chat.id
        welcome_msg = get_welcome_message(chat_id) or DEFAULT_WELCOME_MSG
        
        for new_member in update.message.new_chat_members:
            mention = new_member.mention_html()
            text = welcome_msg.format(
                mention=mention,
                chat_title=update.effective_chat.title,
                username=new_member.username or "user",
                first_name=new_member.first_name or "",
                last_name=new_member.last_name or "",
                full_name=f"{new_member.first_name or ''} {new_member.last_name or ''}".strip()
            )
            await update.message.reply_text(text, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error sending welcome message: {e}")

async def left_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle member leaving the chat"""
    if update.message.left_chat_member.id != context.bot.id:
        await send_goodbye_message(update, context)


async def send_goodbye_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send goodbye message for leaving members"""
    try:
        chat_id = update.effective_chat.id
        goodbye_msg = get_goodbye_message(chat_id) or DEFAULT_GOODBYE_MSG
        
        left_member = update.message.left_chat_member
        mention = left_member.mention_html()
        text = goodbye_msg.format(
            mention=mention,
            chat_title=update.effective_chat.title,
            username=left_member.username or "user",
            first_name=left_member.first_name or "",
            last_name=left_member.last_name or "",
            full_name=f"{left_member.first_name or ''} {left_member.last_name or ''}".strip()
        )
        await update.message.reply_text(text, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error sending goodbye message: {e}")

async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to set custom welcome message"""
    if not await is_group_admin(update, context):
        await update.message.reply_text("❌ You need to be admin to use this command")
        return
    
    if not context.args:
        await update.message.reply_text("ℹ️ Usage: /setwelcome Your welcome message (use {mention}, {chat_title}, etc.)")
        return
    
    welcome_msg = ' '.join(context.args)
    set_welcome_message(update.effective_chat.id, welcome_msg)
    await update.message.reply_text("✅ Welcome message updated and saved!")

async def set_goodbye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to set custom goodbye message"""
    if not await is_group_admin(update, context):
        await update.message.reply_text("❌ You need to be admin to use this command")
        return
    
    if not context.args:
        await update.message.reply_text("ℹ️ Usage: /setgoodbye Your goodbye message (use {mention}, {chat_title}, etc.)")
        return
    
    goodbye_msg = ' '.join(context.args)
    set_goodbye_message(update.effective_chat.id, goodbye_msg)
    await update.message.reply_text("✅ Goodbye message updated and saved!")

async def show_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to show current welcome message"""
    welcome_msg = get_welcome_message(update.effective_chat.id) or DEFAULT_WELCOME_MSG
    await update.message.reply_text(f"Current welcome message:\n\n{welcome_msg}")

async def show_goodbye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to show current goodbye message"""
    goodbye_msg = get_goodbye_message(update.effective_chat.id) or DEFAULT_GOODBYE_MSG
    await update.message.reply_text(f"Current goodbye message:\n\n{goodbye_msg}")

async def auto_upgrade_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Automatically upgrade group to supergroup"""
    try:
        await update.message.reply_text("🔄 Auto-upgrading group...")
        await context.bot.leave_chat(update.effective_chat.id)
    except Exception as e:
        logger.error(f"Upgrade failed: {e}")
        await update.message.reply_text(f"⚠️ Upgrade failed: {e}")

async def is_group_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if the user is an admin in the group"""
    if not update.effective_chat or not update.effective_user:
        return False
    
    try:
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        return any(admin.user.id == update.effective_user.id for admin in admins)
    except Exception as e:
        logger.error(f"Admin check failed: {e}")
        return False

async def get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
async def get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ultimate group member targeting that actually works"""
    try:
        chat = update.effective_chat
        if not chat:
            await update.message.reply_text("❌ This command only works in groups/chats")
            return None

        # 1. First check if replying to a message (most reliable)
        if update.message.reply_to_message:
            return update.message.reply_to_message.from_user

        # 2. Require exactly one argument
        if not context.args or len(context.args) > 1:
            await update.message.reply_text(
                "🔍 <b>How to find users:</b>\n\n"
                "1. Reply to user's message with /info\n"
                "2. /info @username (exact match)\n"
                "3. /info userid\n\n"
                "<i>Note: Usernames are case-sensitive in groups</i>",
                parse_mode="HTML"
            )
            return None

        target = context.args[0].strip()
        
        # 3. Handle numeric IDs (always works if user is in group)
        if target.isdigit():
            try:
                member = await context.bot.get_chat_member(chat.id, int(target))
                return member.user
            except Exception:
                await update.message.reply_text(
                    f"❌ User ID <code>{target}</code> not found in this group",
                    parse_mode="HTML"
                )
                return None

        # 4. Handle username mentions (EXACT match required for groups)
        username = target.lstrip('@')  # Remove @ if present
        
        # SPECIAL CASE: If targeting the bot itself
        if username.lower() == context.bot.username.lower():
            return context.bot.bot

        # Get ALL group members first
        try:
            all_members = []
            async for member in context.bot.get_chat_members(chat.id):
                all_members.append(member.user)
                
            # Check for EXACT username match (case-sensitive!)
            for user in all_members:
                if user.username and user.username == username:  # Exact match
                    return user
                    
            # If no exact match, try case-insensitive
            for user in all_members:
                if user.username and user.username.lower() == username.lower():
                    await update.message.reply_text(
                        f"ℹ️ Found @{user.username} (case mismatch)\n"
                        "In groups, usernames must match exactly",
                        parse_mode="HTML"
                    )
                    return user

            # Final fallback: check name strings
            for user in all_members:
                full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
                if full_name.lower() == username.lower():
                    return user

            await update.message.reply_text(
                f"❌ @{username} not found in this group\n\n"
                "<b>Possible reasons:</b>\n"
                "• User left the group\n"
                "• Username changed\n"
                "• Typo in username\n"
                "• User never joined\n\n"
                "<b>Try:</b>\n"
                "1. Reply to user's message\n"
                "2. Use exact @username\n"
                "3. Ask them to type something",
                parse_mode="HTML"
            )
            return None
            
        except Exception as e:
            logger.error(f"Group member search failed: {str(e)}")
            await update.message.reply_text(
                "⚠️ Failed to search group members\n"
                "Please try:\n"
                "1. Replying to their message\n"
                "2. Using their exact @username\n"
                "3. Using their numeric ID",
                parse_mode="HTML"
            )
            return None

    except Exception as e:
        logger.error(f"CRITICAL targeting error: {str(e)}", exc_info=True)
        await update.message.reply_text(
            "🚨 System error occurred\n"
            "Please contact admin with this info:\n"
            f"Error: {type(e).__name__}",
            parse_mode="HTML"
        )
        return None

def setup_group_handlers(application):
    """Set up all group-related handlers"""
    application.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        new_chat_members
    ))
    application.add_handler(MessageHandler(
        filters.StatusUpdate.LEFT_CHAT_MEMBER,
        left_chat_member
    ))
    application.add_handler(CommandHandler("setwelcome", set_welcome))
    application.add_handler(CommandHandler("setgoodbye", set_goodbye))
    application.add_handler(CommandHandler("welcome", show_welcome))
    application.add_handler(CommandHandler("goodbye", show_goodbye))
