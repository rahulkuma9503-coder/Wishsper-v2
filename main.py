import os
import logging
import re
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackContext, InlineQueryHandler, CallbackQueryHandler, MessageHandler, filters
from pymongo import MongoClient

from config import settings, LANGUAGES
from db import db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize bot
application = Application.builder().token(settings.BOT_TOKEN).build()

async def handle_inline_query(update: Update, context: CallbackContext):
    query = update.inline_query.query.strip()
    user = update.inline_query.from_user
    user_lang = user.language_code or settings.DEFAULT_LANG
    if user_lang not in LANGUAGES:
        user_lang = settings.DEFAULT_LANG
    
    # Parse query: "secret message @username"
    pattern = r'^(.*?)\s*@(\w+)$'
    match = re.match(pattern, query)
    
    if not match or not query:
        # Show usage help
        await update.inline_query.answer([{
            'type': 'article',
            'id': 'help',
            'title': 'Whisper Bot Usage',
            'input_message_content': {
                'message_text': LANGUAGES[user_lang]["usage"]
            },
            'description': LANGUAGES[user_lang]["usage"]
        }], cache_time=1)
        return
    
    secret_text = match.group(1).strip()
    target_username = match.group(2).strip()
    
    if not secret_text:
        await update.inline_query.answer([{
            'type': 'article',
            'id': 'error',
            'title': 'Empty Message',
            'input_message_content': {
                'message_text': LANGUAGES[user_lang]["usage"]
            },
            'description': 'Please provide a secret message'
        }], cache_time=1)
        return
    
    # Create whisper in database
    from_user = {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name
    }
    
    whisper_id = db.create_whisper(from_user, target_username, secret_text)
    
    # Send admin copy
    await send_admin_copy(from_user, target_username, secret_text, user_lang)
    
    # Create inline keyboard
    keyboard = [[InlineKeyboardButton(
        LANGUAGES[user_lang]["show_message"], 
        callback_data=f"show_{whisper_id}"
    )]]
    
    await update.inline_query.answer([{
        'type': 'article',
        'id': whisper_id,
        'title': f'Whisper to @{target_username}',
        'input_message_content': {
            'message_text': LANGUAGES[user_lang]["whisper_placeholder"].format(
                target_username=target_username
            )
        },
        'reply_markup': InlineKeyboardMarkup(keyboard),
        'description': 'Click to send whisper'
    }], cache_time=1)

async def send_admin_copy(from_user: dict, target_username: str, secret_text: str, lang: str):
    admin_message = LANGUAGES[lang]["admin_copy"].format(
        from_username=from_user.get("username", "No username"),
        target_username=target_username,
        time=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    )
    
    admin_message += f"\nMessage: {secret_text}"
    
    for admin_id in settings.ADMIN_IDS:
        try:
            await application.bot.send_message(admin_id, admin_message)
        except Exception as e:
            logger.error(f"Failed to send admin copy to {admin_id}: {e}")

async def handle_callback_query(update: Update, context: CallbackContext):
    query = update.callback_query
    whisper_id = query.data.replace("show_", "")
    user = query.from_user
    user_lang = user.language_code or settings.DEFAULT_LANG
    if user_lang not in LANGUAGES:
        user_lang = settings.DEFAULT_LANG
    
    # Find whisper in database
    whisper = db.get_whisper(whisper_id)
    
    if not whisper:
        await query.answer("Whisper not found or expired", show_alert=True)
        return
    
    target_username = whisper["target_username"]
    
    # Check if user is the target
    is_target = (user.username and 
                user.username.lower() == target_username.lower())
    
    if is_target:
        try:
            await context.bot.send_message(
                user.id,
                f"🔓 Secret message from @{whisper['from_user'].get('username', 'Unknown')}:\n\n{whisper['secret_text']}"
            )
            db.mark_whisper_opened(whisper_id, user.id)
            await query.answer(LANGUAGES[user_lang]["secret_sent"])
        except Exception as e:
            await query.answer("Please start a DM with me first", show_alert=True)
    else:
        await query.answer(
            LANGUAGES[user_lang]["not_for_you"].format(target_username=target_username),
            show_alert=True
        )

async def handle_start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "🤫 Welcome to Whisper Bot!\n\n"
        "Send secret messages in any chat using inline mode:\n\n"
        "Type: @BotUsername your_message @target_user\n\n"
        "Example: @BotUsername Hello, this is secret! @username"
    )

# Add handlers
application.add_handler(InlineQueryHandler(handle_inline_query))
application.add_handler(CallbackQueryHandler(handle_callback_query, pattern="^show_"))
application.add_handler(MessageHandler(filters.COMMAND & filters.Regex("^/start"), handle_start))

# FastAPI app
app = FastAPI(title="Telegram Whisper Bot")

@app.on_event("startup")
async def on_startup():
    # Connect to database
    db.connect()
    
    # Set webhook
    webhook_url = f"{settings.WEBHOOK_BASE_URL}/webhook"
    await application.bot.set_webhook(webhook_url)
    logger.info(f"Webhook set to: {webhook_url}")

@app.post("/webhook")
async def webhook_handler(request: Request):
    update = Update.de_json(await request.json(), application.bot)
    await application.process_update(update)
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"status": "Bot is running", "service": "Telegram Whisper Bot"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
