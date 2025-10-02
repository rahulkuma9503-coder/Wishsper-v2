import os
from typing import List

class Settings:
    def __init__(self):
        self.BOT_TOKEN = os.getenv("BOT_TOKEN")
        self.MONGODB_URI = os.getenv("MONGODB_URI")
        self.WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL")
        self.DEFAULT_LANG = os.getenv("DEFAULT_LANG", "en")
        
        admin_ids = os.getenv("ADMIN_IDS", "")
        self.ADMIN_IDS = [int(id.strip()) for id in admin_ids.split(",") if id.strip()]
        
        if not all([self.BOT_TOKEN, self.MONGODB_URI, self.WEBHOOK_BASE_URL]):
            raise ValueError("Missing required environment variables")

settings = Settings()

LANGUAGES = {
    "en": {
        "usage": "Usage: @BotUsername secret_text @username",
        "whisper_placeholder": "🔒 A whisper message to {target_username} — Only they can open it.",
        "show_message": "show message 🔒",
        "secret_sent": "Secret sent to your DM 🔐",
        "not_for_you": "This whisper is only for @{target_username}",
        "admin_copy": "📨 New Whisper\nFrom: @{from_username}\nTo: @{target_username}\nTime: {time}"
    },
    "hi": {
        "usage": "उपयोग: @BotUsername गुप्त_संदेश @username",
        "whisper_placeholder": "🔒 @{target_username} को एक गुप्त संदेश — केवल वे इसे खोल सकते हैं।",
        "show_message": "संदेश दिखाएं 🔒",
        "secret_sent": "आपके DM में संदेश भेज दिया गया है 🔐",
        "not_for_you": "यह संदेश केवल @{target_username} के लिए है",
        "admin_copy": "📨 नया व्हिस्पर\nभेजने वाला: @{from_username}\nप्राप्तकर्ता: @{target_username}\nसमय: {time}"
    }
}
