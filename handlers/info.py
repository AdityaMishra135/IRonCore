from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from handlers.group import get_target_user
from database.database import get_join_date

async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed information about a user"""
    target = await get_target_user(update, context)
    if not target:
        return
    
    try:
        member = await context.bot.get_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id
        )
        
        # Get join date from our database
        join_date = get_join_date(update.effective_chat.id, target.id)
        
        message = (
            f"👤 <b>User Information</b>\n\n"
            f"🆔 ID: <code>{target.id}</code>\n"
            f"📛 Name: {target.mention_html()}\n"
            f"📅 Joined: {join_date.strftime('%Y-%m-%d %H:%M:%S') if join_date else 'Unknown'}\n"
            f"👑 Status: {member.status}\n"
            f"🤖 Is Bot: {'Yes' if target.is_bot else 'No'}\n"
            f"🔗 Username: @{target.username if target.username else 'N/A'}\n"
            f"📝 Bio: {target.bio if hasattr(target, 'bio') else 'N/A'}"
        )
        
        await update.message.reply_text(message, parse_mode="HTML")
        
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ <b>Info Failed</b>\n\nError: {str(e)}",
            parse_mode="HTML"
        )

def setup_info_handler(app):
    app.add_handler(CommandHandler("info", user_info))
