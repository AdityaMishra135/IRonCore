import os
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

async def new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new members including bot itself"""
    if any(member.id == context.bot.id for member in update.message.new_chat_members):
        if update.effective_chat.type == "group":
            await auto_upgrade_group(update, context)


async def auto_upgrade_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("🔄 Auto-upgrading group...")
        await context.bot.leave_chat(update.effective_chat.id)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Upgrade failed: {e}")

async def is_group_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        member = await update.effective_chat.get_member(update.effective_user.id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False

async def get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fixed username targeting that actually works"""
    try:
        # 1. Check if replying to a message
        if update.message.reply_to_message:
            return update.message.reply_to_message.from_user

        # 2. Check if command has arguments
        if not context.args:
            await update.message.reply_text(
                "ℹ️ Please reply to a user or specify @username/user_id",
                parse_mode="HTML"
            )
            return None

        target = context.args[0].strip()
        
        # 3. Handle @username mentions
        if target.startswith('@'):
            username = target[1:].lower()  # Remove @ and make lowercase
            
            logger.info(f"Searching for username: @{username}")
            
            try:
                # First try with get_chat_member if we have a direct reference
                try:
                    member = await context.bot.get_chat_member(
                        chat_id=update.effective_chat.id,
                        user_id=target
                    )
                    return member.user
                except Exception as e:
                    logger.debug(f"Direct username lookup failed, trying full scan: {e}")

                # Fallback to scanning members
                found_user = None
                member_count = 0
                
                async for member in context.bot.get_chat_members(update.effective_chat.id):
                    member_count += 1
                    user = member.user
                    if user.username and user.username.lower() == username:
                        found_user = user
                        break
                
                if found_user:
                    logger.info(f"Found user after scanning {member_count} members")
                    return found_user
                
                logger.warning(f"Scanned {member_count} members, username not found")
                await update.message.reply_text(f"❌ @{username} not found in this chat")
                return None

            except Exception as e:
                logger.error(f"Username search error: {e}")
                await update.message.reply_text("⚠️ Error searching for user")
                return None

        # 4. Handle numeric IDs
        if target.isdigit():
            try:
                member = await context.bot.get_chat_member(
                    chat_id=update.effective_chat.id,
                    user_id=int(target)
                )
                return member.user
            except Exception as e:
                logger.error(f"ID lookup failed: {e}")
                await update.message.reply_text(f"❌ User ID {target} not found")
                return None

        await update.message.reply_text("⚠️ Invalid target format")
        return None

    except Exception as e:
        logger.error(f"Targeting crashed: {e}", exc_info=True)
        await update.message.reply_text("⚠️ Targeting error occurred")
        return None


def setup_group_handlers(app):
    app.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        new_chat_members
    ))
