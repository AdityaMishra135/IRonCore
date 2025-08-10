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
    """Restrict a user from sending messages (permanent or temporary)"""
    if not await is_group_admin(update, context):
        return
    
    if not (target := await get_target_user(update, context)):
        return
    
    # Default to permanent mute if no duration specified
    until_date = None
    duration_str = "permanently"
    
    # Check if duration is provided
    if len(context.args) > 1:
        try:
            time_str = "".join(context.args[1:]).lower().replace(" ", "")
            seconds = parse_duration(time_str)
            
            if seconds is None:
                await update.message.reply_text(
                    "⚠️ Invalid duration format. Examples: 30s, 5m, 2h, 1d12h",
                    parse_mode="HTML"
                )
                return
            
            # Validate maximum duration (30 days)
            if seconds > 30 * 86400:
                await update.message.reply_text(
                    "⚠️ Maximum mute duration is 30 days",
                    parse_mode="HTML"
                )
                return
                
            until_date = int(time.time()) + seconds
            duration_str = format_duration(seconds)
        except Exception as e:
            await update.message.reply_text(
                f"⚠️ Error parsing duration: {str(e)}",
                parse_mode="HTML"
            )
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
            ),
            until_date=until_date
        )
        
        await update.message.reply_text(
            f"🔇 <b>Muted:</b> {target.mention_html()} (ID: <code>{target.id}</code>)\n"
            f"⏱ <b>Duration:</b> {duration_str}\n"
            f"👮 <b>By admin:</b> {update.effective_user.mention_html()}",
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

def parse_duration(time_str: str) -> int:
    """Parse time duration string into seconds"""
    if not time_str:
        return None
        
    total_seconds = 0
    current_num = ""
    
    for char in time_str:
        if char.isdigit():
            current_num += char
        else:
            if not current_num:
                return None
                
            try:
                num = int(current_num)
            except ValueError:
                return None
                
            if char == 's':
                total_seconds += num
            elif char == 'm':
                total_seconds += num * 60
            elif char == 'h':
                total_seconds += num * 3600
            elif char == 'd':
                total_seconds += num * 86400
            else:
                return None
                
            current_num = ""
    
    # Handle case where string ends with number but no unit
    if current_num:
        return None
        
    return total_seconds if total_seconds > 0 else None

def format_duration(seconds: int) -> str:
    """Format seconds into human-readable duration"""
    if seconds is None:
        return "permanently"
        
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
    
    return " ".join(parts)



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



async def show_usage(update: Update):
    """Show usage instructions"""
    await update.message.reply_text(
        "ℹ️ <b>Usage:</b> <code>/tempmute @username duration</code>\n"
        "📝 <b>Examples:</b>\n"
        "- <code>/tempmute @user 30s</code> (30 seconds)\n"
        "- <code>/tempmute @user 5m</code>\n"
        "- <code>/tempmute @user 2h</code>\n"
        "- <code>/tempmute @user 1d12h</code>\n\n"
        "⏳ <b>Maximum:</b> 30 days",
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

