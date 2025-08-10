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
    """Fully working group member lookup by username"""
    try:
        chat = update.effective_chat
        if not chat or chat.type == "private":
            await update.message.reply_text("❌ This command only works in groups")
            return None

        # 1. Check if replying to a message (most reliable)
        if update.message.reply_to_message:
            return update.message.reply_to_message.from_user

        # 2. Require exactly one argument
        if not context.args or len(context.args) != 1:
            await update.message.reply_text(
                "🔍 <b>Usage:</b> /info @username\n"
                "or reply to user's message with /info",
                parse_mode="HTML"
            )
            return None

        target = context.args[0].strip().lstrip('@')
        
        # 3. Get ALL group members (this is the key part)
        members = []
        async for member in context.bot.get_chat_members(chat.id):
            user = member.user
            members.append({
                'user_obj': user,
                'username': user.username.lower() if user.username else None,
                'full_name': f"{user.first_name or ''} {user.last_name or ''}".strip().lower()
            })

        # 4. Search through members (prioritize exact matches)
        exact_match = None
        case_insensitive_match = None
        
        for member in members:
            # Check exact username match (case sensitive)
            if member['user_obj'].username == target:
                return member['user_obj']
                
            # Check case-insensitive username match
            if member['username'] == target.lower():
                case_insensitive_match = member['user_obj']
                
            # Check name match
            if member['full_name'] == target.lower():
                case_insensitive_match = member['user_obj']

        # 5. Handle the search results
        if case_insensitive_match:
            await update.message.reply_text(
                f"ℹ️ Found similar user: @{case_insensitive_match.username}\n"
                "Note: Usernames in groups are case-sensitive",
                parse_mode="HTML"
            )
            return case_insensitive_match

        await update.message.reply_text(
            f"❌ @{target} not found in this group\n\n"
            "<b>Possible reasons:</b>\n"
            "• User left the group\n"
            "• Username changed\n"
            "• Typo in username\n\n"
            "<b>Try:</b>\n"
            "1. Reply to user's message\n"
            "2. Check exact username case\n"
            "3. Use /info without arguments for help",
            parse_mode="HTML"
        )
        return None

    except Exception as e:
        logger.error(f"User lookup failed: {str(e)}")
        await update.message.reply_text(
            "⚠️ Error searching group members\n"
            "Please try again or contact admin",
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
