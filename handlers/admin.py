import os
from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes, CommandHandler
from handlers.group import is_group_admin, get_target_user

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_group_admin(update, context):
        return
    
    if not (target := await get_target_user(update, context)):
        return
    
    try:
        await context.bot.ban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id
        )
        await update.message.reply_text(
            f"🚫 Banned: {target.mention_html()} (ID: {target.id})",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ban failed: {e}")

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


def setup_admin_handlers(app):
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("kick", kick_user))
    app.add_handler(CommandHandler("mute", mute_user))
