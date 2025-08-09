import time
from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes, CommandHandler
from handlers.group import is_group_admin, get_target_user

# Warning storage (replace with database in production)
WARNINGS_DB = {}

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Soft ban - restrict all permissions without kicking"""
    if not await is_group_admin(update, context):
        return
    
    if not (target := await get_target_user(update, context)):
        return
    
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "No reason provided"
    
    try:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id,
            permissions=ChatPermissions(
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False,
                can_send_polls=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False
            )
        )
        
        # Clear warnings if any
        if target.id in WARNINGS_DB:
            del WARNINGS_DB[target.id]
        
        await update.message.reply_text(
            f"🚫 <b>Banned:</b> {target.mention_html()} (ID: <code>{target.id}</code>)\n"
            f"📝 <b>Reason:</b> {reason}\n\n"
            f"User remains in group but cannot perform any actions.",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ <b>Ban Failed:</b> {str(e)}",
            parse_mode="HTML"
        )

async def hard_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Original ban (remove from group)"""
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
            f"🚫 <b>Hard Banned:</b> {target.mention_html()} (ID: <code>{target.id}</code>)",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ban failed: {e}")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restore all permissions to a banned user"""
    if not await is_group_admin(update, context):
        return
    
    if not (target := await get_target_user(update, context)):
        return
    
    try:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_send_polls=True,
                can_change_info=True,
                can_invite_users=True,
                can_pin_messages=True
            )
        )
        await update.message.reply_text(
            f"✅ <b>Unbanned:</b> {target.mention_html()} (ID: <code>{target.id}</code>)",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ <b>Unban Failed:</b> {str(e)}",
            parse_mode="HTML"
        )

async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Warn a user (3 warnings = auto ban)"""
    if not await is_group_admin(update, context):
        return
    
    if not (target := await get_target_user(update, context)):
        return
    
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "No reason provided"
    
    # Initialize warnings if new user
    if target.id not in WARNINGS_DB:
        WARNINGS_DB[target.id] = []
    
    # Add warning
    WARNINGS_DB[target.id].append({
        'time': time.time(),
        'reason': reason,
        'by': update.effective_user.id
    })
    
    warning_count = len(WARNINGS_DB[target.id])
    
    # Auto-ban at 3 warnings
    if warning_count >= 3:
        try:
            await ban_user(update, context)
            warning_history = "\n".join(
                f"{i+1}. {w['reason']} (by admin {w['by']})" 
                for i, w in enumerate(WARNINGS_DB[target.id])
            )
            await update.message.reply_text(
                f"⚠️ <b>Auto-Banned:</b> {target.mention_html()} after 3 warnings\n\n"
                f"📜 <b>Warning History:</b>\n{warning_history}",
                parse_mode="HTML"
            )
            del WARNINGS_DB[target.id]
            return
        except Exception as e:
            await update.message.reply_text(
                f"⚠️ <b>Auto-Ban Failed:</b> {str(e)}",
                parse_mode="HTML"
            )
            return
    
    await update.message.reply_text(
        f"⚠️ <b>Warning issued to {target.mention_html()}</b>\n"
        f"📝 <b>Reason:</b> {reason}\n"
        f"🔢 <b>Warnings:</b> {warning_count}/3",
        parse_mode="HTML"
    )

async def check_warnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check a user's warnings"""
    if not (target := await get_target_user(update, context)):
        return
    
    if target.id not in WARNINGS_DB or not WARNINGS_DB[target.id]:
        await update.message.reply_text("ℹ️ This user has no warnings")
        return
    
    warning_history = "\n".join(
        f"{i+1}. {w['reason']} (by admin {w['by']})" 
        for i, w in enumerate(WARNINGS_DB[target.id])
    )
    
    await update.message.reply_text(
        f"⚠️ <b>Warnings for {target.mention_html()}</b>\n\n"
        f"🔢 <b>Total:</b> {len(WARNINGS_DB[target.id])}/3\n"
        f"📜 <b>History:</b>\n{warning_history}",
        parse_mode="HTML"
    )

# Your original functions remain unchanged
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
    
    if not (target := await get_target_user(update, context)):
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

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove all restrictions from a user"""
    if not await is_group_admin(update, context):
        return
    
    if not (target := await get_target_user(update, context)):
        return
    
    try:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
        await update.message.reply_text(
            f"🔊 <b>Unmuted:</b> {target.mention_html()} (ID: <code>{target.id}</code>)",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ <b>Unmute Failed</b>\n\n"
            f"Error: {str(e)}\n\n"
            f"Possible reasons:\n"
            f"- I need admin permissions\n"
            f"- User not muted",
            parse_mode="HTML"
        )

async def temp_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Temporarily mute a user (usage: /tempmute @username 1h30m)"""
    if not await is_group_admin(update, context):
        return
    
    # Check if we have both target and time
    if len(context.args) < 2:
        await update.message.reply_text(
            "ℹ️ <b>Usage:</b> <code>/tempmute @username 1h30m</code>\n"
            "📝 <b>Supported time units:</b> m (minutes), h (hours), d (days)\n"
            "⏱ <b>Examples:</b> 30m, 2h, 1d12h, 1h30m",
            parse_mode="HTML"
        )
        return
    
    # Get target user
    target = await get_target_user(update, context)
    if not target:
        return
    
    # Parse time duration (handle spaces between number and unit)
    time_input = context.args[1].lower().replace(" ", "")
    
    if not any(unit in time_input for unit in ['m', 'h', 'd']):
        await update.message.reply_text(
            "⚠️ <b>Invalid time format</b>\n"
            "Please include time units (m/h/d)\n"
            "Example: <code>/tempmute @user 1h30m</code>",
            parse_mode="HTML"
        )
        return
    
    seconds = 0
    try:
        # Parse days
        if 'd' in time_input:
            days_part = time_input.split('d')[0]
            if days_part:
                days = int(days_part)
                seconds += days * 86400
            time_input = time_input.split('d', 1)[-1]
        
        # Parse hours
        if 'h' in time_input:
            hours_part = time_input.split('h')[0]
            if hours_part:
                hours = int(hours_part)
                seconds += hours * 3600
            time_input = time_input.split('h', 1)[-1]
        
        # Parse minutes
        if 'm' in time_input:
            minutes_part = time_input.split('m')[0]
            if minutes_part:
                minutes = int(minutes_part)
                seconds += minutes * 60
    except ValueError:
        await update.message.reply_text(
            "⚠️ <b>Invalid number in time format</b>\n"
            "Use format like: <code>1h30m</code>",
            parse_mode="HTML"
        )
        return
    
    # Validate duration
    if seconds < 60:
        await update.message.reply_text(
            "⚠️ <b>Minimum mute duration is 1 minute</b>\n"
            "Please use at least <code>1m</code>",
            parse_mode="HTML"
        )
        return
    
    if seconds > 30 * 86400:  # 30 days max
        await update.message.reply_text(
            "⚠️ <b>Maximum mute duration is 30 days</b>",
            parse_mode="HTML"
        )
        return
    
    # Apply the mute
    try:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id,
            permissions=ChatPermissions(
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False
            ),
            until_date=int(time.time()) + seconds
        )
        
        # Format duration for display
        duration_parts = []
        remaining = seconds
        if remaining >= 86400:
            days = remaining // 86400
            duration_parts.append(f"{days}d")
            remaining %= 86400
        if remaining >= 3600:
            hours = remaining // 3600
            duration_parts.append(f"{hours}h")
            remaining %= 3600
        if remaining >= 60:
            minutes = remaining // 60
            duration_parts.append(f"{minutes}m")
        
        await update.message.reply_text(
            f"⏳ <b>Temporarily muted:</b> {target.mention_html()}\n"
            f"⏱ <b>Duration:</b> {' '.join(duration_parts)}\n"
            f"👮 <b>By admin:</b> {update.effective_user.mention_html()}",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ <b>Failed to mute user</b>\n"
            f"Error: {str(e)}",
            parse_mode="HTML"
        )

def setup_admin_handlers(app):
    app.add_handler(CommandHandler("ban", ban_user))  # Soft ban
    app.add_handler(CommandHandler("hardban", hard_ban))  # Original ban
    app.add_handler(CommandHandler("unban", unban_user))
    app.add_handler(CommandHandler("warn", warn_user))
    app.add_handler(CommandHandler("warnings", check_warnings))
    app.add_handler(CommandHandler("kick", kick_user))
    app.add_handler(CommandHandler("mute", mute_user))
    app.add_handler(CommandHandler("unmute", unmute_user))
    app.add_handler(CommandHandler("tempmute", temp_mute))
