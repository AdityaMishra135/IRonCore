import os
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from handlers.group import get_target_user, get_user_join_date
from datetime import datetime

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
        
        # Get join date from our storage first, then fallback to Telegram's data
        stored_join_date = get_user_join_date(update.effective_chat.id, target.id)
        join_date = (
            stored_join_date.strftime("%Y-%m-%d %H:%M:%S") if stored_join_date else
            member.joined_date.strftime("%Y-%m-%d %H:%M:%S") if hasattr(member, 'joined_date') and member.joined_date else
            "Owner/Creator"
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

def setup_info_handler(app):
    app.add_handler(CommandHandler("info", user_info))
