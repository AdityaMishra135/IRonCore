import random
from telegram import (
    Update,
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ContextTypes,
    MessageHandler,
    filters,
    CommandHandler,
    CallbackQueryHandler
)
from datetime import datetime, timedelta

# CAPTCHA configuration
CAPTCHA_TIMEOUT = 300  # 5 minutes in seconds
PENDING_VERIFICATION = {}  # Stores pending users: {chat_id: {user_id: {"answer": X, "msg_id": Y}}}

async def new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new members with CAPTCHA verification"""
    # Check if bot was added
    if any(member.id == context.bot.id for member in update.message.new_chat_members):
        if update.effective_chat.type == "group":
            await auto_upgrade_group(update, context)
        return
    
    # Skip if not a group/supergroup
    if update.effective_chat.type not in ["group", "supergroup"]:
        return
    
    # Restrict and verify each new member
    for member in update.message.new_chat_members:
        if member.is_bot:  # Skip other bots
            continue
            
        await start_captcha_verification(update, context, member)

async def start_captcha_verification(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    """Initiate CAPTCHA verification for a user"""
    chat = update.effective_chat
    user_id = user.id
    
    # Generate simple math CAPTCHA (e.g., "2 + 3")
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    answer = num1 + num2
    captcha_text = f"{num1} + {num2} = ?"
    
    # Restrict user permissions
    await context.bot.restrict_chat_member(
        chat_id=chat.id,
        user_id=user_id,
        permissions=ChatPermissions(
            can_send_messages=False,
            can_send_media_messages=False,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False
        )
    )
    
    # Store CAPTCHA answer
    if chat.id not in PENDING_VERIFICATION:
        PENDING_VERIFICATION[chat.id] = {}
    
    # Send CAPTCHA message with button
    keyboard = [[InlineKeyboardButton("Click to solve CAPTCHA", callback_data=f"captcha_{user_id}")]]
    msg = await context.bot.send_message(
        chat_id=chat.id,
        text=f"👋 Welcome {user.mention_html()}! Please verify you're human:\n\n"
             f"🔢 Solve this: {captcha_text}\n"
             f"⚠️ You have {CAPTCHA_TIMEOUT//60} minutes to complete this.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    # Store verification data
    PENDING_VERIFICATION[chat.id][user_id] = {
        "answer": answer,
        "msg_id": msg.message_id,
        "join_time": datetime.now()
    }
    
    # Schedule auto-kick if not solved
    context.job_queue.run_once(
        callback=auto_kick_user,
        when=CAPTCHA_TIMEOUT,
        data=(chat.id, user_id),
        name=f"captcha_kick_{chat.id}_{user_id}"
    )

async def handle_captcha_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle CAPTCHA button press"""
    query = update.callback_query
    user_id = int(query.data.split("_")[1])
    chat_id = update.effective_chat.id
    
    # Verify this is the correct user clicking
    if query.from_user.id != user_id:
        await query.answer("This CAPTCHA isn't for you!", show_alert=True)
        return
    
    # Check if user is still pending verification
    if chat_id not in PENDING_VERIFICATION or user_id not in PENDING_VERIFICATION[chat_id]:
        await query.answer("Verification expired!", show_alert=True)
        return
    
    # Ask for the answer via private message
    await query.answer()
    await context.bot.send_message(
        chat_id=user_id,
        text=f"Please send me the answer to the CAPTCHA you saw in the group."
    )

async def verify_captcha_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check user's answer to CAPTCHA"""
    user_id = update.effective_user.id
    chat_id = None
    
    # Find which chat this user is verifying for
    for cid, users in PENDING_VERIFICATION.items():
        if user_id in users:
            chat_id = cid
            break
    
    if not chat_id:
        return  # Not in verification process
    
    captcha_data = PENDING_VERIFICATION[chat_id][user_id]
    
    try:
        # Check if answer is correct
        if int(update.message.text.strip()) == captcha_data["answer"]:
            # Grant full permissions
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_polls=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True
                )
            )
            
            # Delete CAPTCHA message
            try:
                await context.bot.delete_message(
                    chat_id=chat_id,
                    message_id=captcha_data["msg_id"]
                )
            except:
                pass
            
            # Remove from pending
            del PENDING_VERIFICATION[chat_id][user_id]
            
            # Send welcome message
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ {update.effective_user.mention_html()} has passed verification! Welcome!",
                parse_mode="HTML"
            )
            
            # Cancel auto-kick job
            for job in context.job_queue.get_jobs_by_name(f"captcha_kick_{chat_id}_{user_id}"):
                job.schedule_removal()
        else:
            await update.message.reply_text("❌ Wrong answer! Try again.")
    except ValueError:
        await update.message.reply_text("Please send a number only!")

async def auto_kick_user(context: ContextTypes.DEFAULT_TYPE):
    """Auto-kick users who don't solve CAPTCHA"""
    job = context.job
    chat_id, user_id = job.data
    
    if chat_id not in PENDING_VERIFICATION or user_id not in PENDING_VERIFICATION[chat_id]:
        return
    
    try:
        # Kick user
        await context.bot.ban_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            until_date=datetime.now() + timedelta(seconds=30)  # Temp ban
        
        # Delete CAPTCHA message
        try:
            await context.bot.delete_message(
                chat_id=chat_id,
                message_id=PENDING_VERIFICATION[chat_id][user_id]["msg_id"]
            )
        except:
            pass
        
        # Notify group
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ User was removed for not completing verification."
        )
    except Exception as e:
        print(f"Failed to kick user: {e}")
    finally:
        # Clean up
        if chat_id in PENDING_VERIFICATION and user_id in PENDING_VERIFICATION[chat_id]:
            del PENDING_VERIFICATION[chat_id][user_id]

def setup_group_handlers(app):
    # New member handler
    app.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        new_chat_members
    ))
    
    # Left member handler
    app.add_handler(MessageHandler(
        filters.StatusUpdate.LEFT_CHAT_MEMBER,
        left_chat_member
    ))
    
    # CAPTCHA button handler
    app.add_handler(CallbackQueryHandler(
        handle_captcha_button,
        pattern="^captcha_"
    ))
    
    # CAPTCHA answer handler
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        verify_captcha_answer
    ))
