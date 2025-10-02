import os
import logging
import re
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackContext, InlineQueryHandler, CallbackQueryHandler, MessageHandler, filters
from pymongo import MongoClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get environment variables with defaults
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
MONGODB_URI = os.getenv("MONGODB_URI", "").strip()
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "").strip()
DEFAULT_LANG = os.getenv("DEFAULT_LANG", "en").strip()

admin_ids = os.getenv("ADMIN_IDS", "").strip()
ADMIN_IDS = [int(id.strip()) for id in admin_ids.split(",") if id.strip()]

# Debug info
logger.info("🔧 Environment Variables:")
logger.info(f"BOT_TOKEN: {'✅ Set' if BOT_TOKEN else '❌ Missing'}")
logger.info(f"MONGODB_URI: {'✅ Set' if MONGODB_URI else '❌ Missing'}")
logger.info(f"WEBHOOK_BASE_URL: {'✅ Set' if WEBHOOK_BASE_URL else '❌ Missing'}")
logger.info(f"ADMIN_IDS: {ADMIN_IDS}")

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN is required!")
if not MONGODB_URI:
    logger.error("❌ MONGODB_URI is required!")
if not WEBHOOK_BASE_URL:
    logger.error("❌ WEBHOOK_BASE_URL is required!")

LANGUAGES = {
    "en": {
        "usage": "Usage: @BotUsername secret_text @username",
        "whisper_placeholder": "🔒 A whisper message to {target_username} — Only they can open it.",
        "show_message": "show message 🔒",
        "secret_sent": "Secret sent to your DM 🔐",
        "not_for_you": "This whisper is only for @{target_username}",
        "admin_copy": "📨 New Whisper\nFrom: @{from_username}\nTo: @{target_username}\nTime: {time}"
    }
}

# Initialize bot only if token is available
if BOT_TOKEN:
    application = Application.builder().token(BOT_TOKEN).build()
else:
    application = None
    logger.error("❌ Bot cannot start without BOT_TOKEN")

class Database:
    def __init__(self):
        self.client = None
        self.db = None
        self.whispers = None

    def connect(self):
        if not MONGODB_URI:
            logger.error("❌ Cannot connect to MongoDB: MONGODB_URI not set")
            return
        try:
            self.client = MongoClient(MONGODB_URI)
            self.db = self.client.whisper_bot
            self.whispers = self.db.whispers
            self.whispers.create_index([("created_at", -1)])
            logger.info("✅ Connected to MongoDB")
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")

    def close(self):
        if self.client:
            self.client.close()

    def create_whisper(self, from_user: dict, target_username: str, secret_text: str) -> str:
        from bson import ObjectId
        from datetime import datetime
        
        if not self.whispers:
            return "demo_whisper_id"
            
        whisper_id = str(ObjectId())
        whisper_data = {
            "whisper_id": whisper_id,
            "from_user": from_user,
            "target_username": target_username.lower().replace("@", ""),
            "secret_text": secret_text,
            "created_at": datetime.utcnow(),
            "opened_at": None,
            "opened_by": None
        }
        self.whispers.insert_one(whisper_data)
        return whisper_id

    def get_whisper(self, whisper_id: str):
        if not self.whispers:
            return None
        return self.whispers.find_one({"whisper_id": whisper_id})

db = Database()

async def handle_inline_query(update: Update, context: CallbackContext):
    if not application:
        return
        
    query = update.inline_query.query.strip()
    user = update.inline_query.from_user
    user_lang = user.language_code or DEFAULT_LANG
    
    # Parse query
    pattern = r'^(.*?)\s*@(\w+)$'
    match = re.match(pattern, query)
    
    if not match or not query:
        await update.inline_query.answer([{
            'type': 'article',
            'id': 'help',
            'title': 'Whisper Bot Usage',
            'input_message_content': {'message_text': LANGUAGES["en"]["usage"]},
            'description': LANGUAGES["en"]["usage"]
        }], cache_time=1)
        return
    
    secret_text = match.group(1).strip()
    target_username = match.group(2).strip()
    
    if not secret_text:
        await update.inline_query.answer([{
            'type': 'article',
            'id': 'error',
            'title': 'Empty Message',
            'input_message_content': {'message_text': LANGUAGES["en"]["usage"]},
            'description': 'Please provide a secret message'
        }], cache_time=1)
        return
    
    # Create whisper
    from_user = {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name
    }
    
    whisper_id = db.create_whisper(from_user, target_username, secret_text)
    
    # Create inline keyboard
    keyboard = [[InlineKeyboardButton("show message 🔒", callback_data=f"show_{whisper_id}")]]
    
    await update.inline_query.answer([{
        'type': 'article',
        'id': whisper_id,
        'title': f'Whisper to @{target_username}',
        'input_message_content': {
            'message_text': f"🔒 A whisper message to {target_username} — Only they can open it."
        },
        'reply_markup': InlineKeyboardMarkup(keyboard),
        'description': 'Click to send whisper'
    }], cache_time=1)

async def handle_callback_query(update: Update, context: CallbackContext):
    query = update.callback_query
    whisper_id = query.data.replace("show_", "")
    user = query.from_user
    
    whisper = db.get_whisper(whisper_id)
    
    if not whisper:
        await query.answer("Whisper not found", show_alert=True)
        return
    
    target_username = whisper["target_username"]
    is_target = (user.username and user.username.lower() == target_username.lower())
    
    if is_target:
        try:
            await context.bot.send_message(
                user.id,
                f"🔓 Secret message from @{whisper['from_user'].get('username', 'Unknown')}:\n\n{whisper['secret_text']}"
            )
            await query.answer("Secret sent to your DM 🔐")
        except Exception:
            await query.answer("Please start a DM with me first", show_alert=True)
    else:
        await query.answer(f"This whisper is only for @{target_username}", show_alert=True)

# Add handlers only if application exists
if application:
    application.add_handler(InlineQueryHandler(handle_inline_query))
    application.add_handler(CallbackQueryHandler(handle_callback_query, pattern="^show_"))

app = FastAPI(title="Telegram Whisper Bot")

@app.on_event("startup")
async def on_startup():
    db.connect()
    if application and WEBHOOK_BASE_URL:
        webhook_url = f"{WEBHOOK_BASE_URL}/webhook"
        await application.bot.set_webhook(webhook_url)
        logger.info(f"✅ Webhook set to: {webhook_url}")
    else:
        logger.warning("⚠️  Bot not fully configured")

@app.post("/webhook")
async def webhook_handler(request: Request):
    if not application:
        return {"status": "bot not configured"}
    
    update = Update.de_json(await request.json(), application.bot)
    await application.process_update(update)
    return {"status": "ok"}

@app.get("/")
async def root():
    return {
        "status": "Bot is running" if BOT_TOKEN else "Bot not configured",
        "bot_configured": bool(BOT_TOKEN),
        "database_configured": bool(MONGODB_URI)
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
