import os
from typing import List

class Settings:
    def __init__(self):
        self.BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
        self.MONGODB_URI = os.getenv("MONGODB_URI", "").strip()
        self.WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "").strip()
        self.DEFAULT_LANG = os.getenv("DEFAULT_LANG", "en").strip()
        
        admin_ids = os.getenv("ADMIN_IDS", "").strip()
        self.ADMIN_IDS = [int(id.strip()) for id in admin_ids.split(",") if id.strip()]
        
        # Debug information
        print("🔧 Environment Variables Check:")
        print(f"BOT_TOKEN: {'✅ Set' if self.BOT_TOKEN else '❌ Missing'}")
        print(f"MONGODB_URI: {'✅ Set' if self.MONGODB_URI else '❌ Missing'}")
        print(f"WEBHOOK_BASE_URL: {'✅ Set' if self.WEBHOOK_BASE_URL else '❌ Missing'}")
        print(f"ADMIN_IDS: {self.ADMIN_IDS}")
        
        # Validate required environment variables
        if not self.BOT_TOKEN:
            raise ValueError("❌ BOT_TOKEN is required")
        if not self.MONGODB_URI:
            raise ValueError("❌ MONGODB_URI is required")
        if not self.WEBHOOK_BASE_URL:
            raise ValueError("❌ WEBHOOK_BASE_URL is required")

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
