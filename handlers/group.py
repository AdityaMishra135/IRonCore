import os
import logging
from telegram import Update
from telegram.ext import (
    ContextTypes,
    MessageHandler,
    filters,
    CommandHandler,
    ApplicationBuilder
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

async def new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new members including bot itself"""
    try:
        # Check if bot was added to the group
        if any(member.id == context.bot.id for member in update.message.new_chat_members):
            if update.effective_chat.type == "group":
                await auto_upgrade_group(update, context)
            return  # Don't proceed further if bot was added
        
        # Initialize welcome message if not set
        if 'welcome_msg' not in context.chat_data:
            context.chat_data['welcome_msg'] = DEFAULT_WELCOME_MSG
        
        # Handle user join greetings
        await send_welcome_message(update, context)
    except Exception as e:
        logger.error(f"Error in new_chat_members: {e}", exc_info=True)

async def send_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message for new members"""
    try:
        chat_id = str(update.effective_chat.id)
        
        # Get welcome message with fallbacks
        welcome_msg = context.bot_data.get('welcome_msgs', {}).get(
            chat_id,
            context.chat_data.get('welcome_msg', DEFAULT_WELCOME_MSG)
        )
        
        for new_member in update.message.new_chat_members:
            # Skip if the new member is the bot itself
            if new_member.id == context.bot.id:
                continue
                
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
        logger.error(f"Error sending welcome message: {e}", exc_info=True)

async def left_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle member leaving the chat"""
    try:
        if update.message.left_chat_member.id != context.bot.id:
            await send_goodbye_message(update, context)
    except Exception as e:
        logger.error(f"Error in left_chat_member: {e}", exc_info=True)

async def send_goodbye_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send goodbye message for leaving members"""
    try:
        chat_id = str(update.effective_chat.id)
        
        # Get goodbye message with fallbacks
        goodbye_msg = context.bot_data.get('goodbye_msgs', {}).get(
            chat_id,
            context.chat_data.get('goodbye_msg', DEFAULT_GOODBYE_MSG)
        )
        
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
        logger.error(f"Error sending goodbye message: {e}", exc_info=True)

async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to set custom welcome message"""
    try:
        if not await is_group_admin(update, context):
            await update.message.reply_text("❌ You need to be admin to use this command")
            return
        
        if not context.args:
            await update.message.reply_text(
                "ℹ️ Usage: /setwelcome Your welcome message\n"
                "Available placeholders: {mention}, {chat_title}, {username}, "
                "{first_name}, {last_name}, {full_name}"
            )
            return
        
        welcome_msg = ' '.join(context.args)
        chat_id = str(update.effective_chat.id)
        
        # Update both chat_data (memory) and bot_data (persistent)
        context.chat_data['welcome_msg'] = welcome_msg
        
        if 'welcome_msgs' not in context.bot_data:
            context.bot_data['welcome_msgs'] = {}
        context.bot_data['welcome_msgs'][chat_id] = welcome_msg
        
        await update.message.reply_text("✅ Welcome message updated!")
    except Exception as e:
        logger.error(f"Error in set_welcome: {e}", exc_info=True)
        await update.message.reply_text("⚠️ Failed to update welcome message")

async def set_goodbye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to set custom goodbye message"""
    try:
        if not await is_group_admin(update, context):
            await update.message.reply_text("❌ You need to be admin to use this command")
            return
        
        if not context.args:
            await update.message.reply_text(
                "ℹ️ Usage: /setgoodbye Your goodbye message\n"
                "Available placeholders: {mention}, {chat_title}, {username}, "
                "{first_name}, {last_name}, {full_name}"
            )
            return
        
        goodbye_msg = ' '.join(context.args)
        chat_id = str(update.effective_chat.id)
        
        # Update both chat_data (memory) and bot_data (persistent)
        context.chat_data['goodbye_msg'] = goodbye_msg
        
        if 'goodbye_msgs' not in context.bot_data:
            context.bot_data['goodbye_msgs'] = {}
        context.bot_data['goodbye_msgs'][chat_id] = goodbye_msg
        
        await update.message.reply_text("✅ Goodbye message updated!")
    except Exception as e:
        logger.error(f"Error in set_goodbye: {e}", exc_info=True)
        await update.message.reply_text("⚠️ Failed to update goodbye message")

async def show_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to show current welcome message"""
    try:
        chat_id = str(update.effective_chat.id)
        welcome_msg = context.bot_data.get('welcome_msgs', {}).get(
            chat_id,
            context.chat_data.get('welcome_msg', DEFAULT_WELCOME_MSG)
        )
        await update.message.reply_text(f"Current welcome message:\n\n{welcome_msg}")
    except Exception as e:
        logger.error(f"Error in show_welcome: {e}", exc_info=True)

async def show_goodbye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to show current goodbye message"""
    try:
        chat_id = str(update.effective_chat.id)
        goodbye_msg = context.bot_data.get('goodbye_msgs', {}).get(
            chat_id,
            context.chat_data.get('goodbye_msg', DEFAULT_GOODBYE_MSG)
        )
        await update.message.reply_text(f"Current goodbye message:\n\n{goodbye_msg}")
    except Exception as e:
        logger.error(f"Error in show_goodbye: {e}", exc_info=True)

async def auto_upgrade_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Automatically upgrade group to supergroup"""
    try:
        await update.message.reply_text("🔄 Auto-upgrading group...")
        await context.bot.leave_chat(update.effective_chat.id)
    except Exception as e:
        logger.error(f"Upgrade failed: {e}", exc_info=True)
        await update.message.reply_text(f"⚠️ Upgrade failed: {e}")

async def is_group_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if the user is an admin in the group"""
    try:
        if not update.effective_chat or not update.effective_user:
            return False
        
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        return any(admin.user.id == update.effective_user.id for admin in admins)
    except Exception as e:
        logger.error(f"Admin check failed: {e}", exc_info=True)
        return False

def setup_handlers(application):
    """Set up all handlers"""
    # Group handlers
    group_handlers = [
        MessageHandler(
            filters.ChatType.GROUPS & filters.StatusUpdate.NEW_CHAT_MEMBERS,
            new_chat_members
        ),
        MessageHandler(
            filters.ChatType.GROUPS & filters.StatusUpdate.LEFT_CHAT_MEMBER,
            left_chat_member
        ),
        CommandHandler("setwelcome", set_welcome, filters.ChatType.GROUPS),
        CommandHandler("setgoodbye", set_goodbye, filters.ChatType.GROUPS),
        CommandHandler("welcome", show_welcome, filters.ChatType.GROUPS),
        CommandHandler("goodbye", show_goodbye, filters.ChatType.GROUPS)
    ]
    
    for handler in group_handlers:
        application.add_handler(handler)

def main():
    """Start the bot"""
    # Create the Application
    application = ApplicationBuilder() \
        .token(os.getenv("TELEGRAM_BOT_TOKEN")) \
        .build()
    
    # Set up handlers
    setup_handlers(application)
    
    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
