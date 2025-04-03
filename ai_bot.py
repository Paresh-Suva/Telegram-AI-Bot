import os
import logging
import random
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackContext,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

# ====== CONFIGURATION ====== #
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
OWNER_ID = 1206054854  # Your Telegram ID
CHANNEL_USERNAME = "@MemeAddictsDaily"  # Your channel

# API Endpoints
API_URLS = {
    "wiki": "https://en.wikipedia.org/api/rest_v1/page/summary/",
    "quiz": "https://opentdb.com/api.php?amount=1&type=multiple",
    "weather": f"https://api.openweathermap.org/data/2.5/weather?appid={WEATHER_API_KEY}&units=metric",
    "fact": "https://uselessfacts.jsph.pl/random.json?language=en",
    "joke": "https://v2.jokeapi.dev/joke/Any",
    "word": "https://random-word-api.herokuapp.com/word",
    "currency": "https://api.exchangerate-api.com/v4/latest/USD"
}

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====== CORE FUNCTIONS ====== #
async def is_member(user_id: int, context: CallbackContext) -> bool:
    """Check if user is in channel"""
    if user_id == OWNER_ID:
        return True
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Membership check failed: {e}")
        return False

async def enforce_membership(update: Update, context: CallbackContext):
    """Ensure user joins channel"""
    if not await is_member(update.effective_user.id, context):
        await update.message.reply_text(
            f"🔒 Join {CHANNEL_USERNAME} first!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
                [InlineKeyboardButton("✅ Verify", callback_data="verify")]
            ])
        )
        return False
    return True

# ====== HANDLERS ====== #
async def start(update: Update, context: CallbackContext):
    """Main menu"""
    await update.message.reply_text(
        "🌟 **Multi-Feature Bot** 🌟\n\n"
        "📚 /wiki - Search Wikipedia\n"
        "❓ /quiz - Take a quiz\n"
        "⛅ /weather - Check weather\n"
        "💱 /currency - Exchange rates\n"
        "📚 /fact - Random fact\n"
        "😂 /joke - Random joke\n"
        "📖 /word - Random word",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Wiki", callback_data="wiki")],
            [InlineKeyboardButton("😂 Joke", callback_data="joke")]
        ])
    )

async def handle_wiki(update: Update, context: CallbackContext):
    """Wikipedia search"""
    if not await enforce_membership(update, context):
        return
    
    if update.message.text == "/wiki":
        await update.message.reply_text("🔍 Enter a topic:")
        context.user_data["awaiting_wiki"] = True
        return
    
    try:
        topic = update.message.text
        res = requests.get(f"{API_URLS['wiki']}{topic}").json()
        await update.message.reply_text(f"📖 {res['title']}\n\n{res['extract']}")
    except Exception as e:
        logger.error(f"Wiki error: {e}")
        await update.message.reply_text("❌ Wikipedia error. Try /fact")

async def handle_joke(update: Update, context: CallbackContext):
    """Random joke"""
    if not await enforce_membership(update, context):
        return
    
    try:
        joke = requests.get(API_URLS["joke"]).json()
        text = joke["setup"] + "\n\n" + joke["delivery"] if joke["type"] == "twopart" else joke["joke"]
        await update.message.reply_text(f"😂 {text}")
    except Exception as e:
        logger.error(f"Joke error: {e}")
        await update.message.reply_text("❌ Joke API failed. Try /fact")

# (Add other handlers similarly...)

async def verify_membership(update: Update, context: CallbackContext):
    """Verify user joined channel"""
    query = update.callback_query
    await query.answer()
    
    if await is_member(query.from_user.id, context):
        await query.edit_message_text("✅ Access granted! Use /start")
    else:
        await query.edit_message_text("❌ Still not joined. Try again.")

# ====== BOT SETUP ====== #
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("wiki", handle_wiki))
    app.add_handler(CommandHandler("joke", handle_joke))
    # (Add other commands...)

    # Callbacks
    app.add_handler(CallbackQueryHandler(handle_wiki, pattern="^wiki$"))
    app.add_handler(CallbackQueryHandler(handle_joke, pattern="^joke$"))
    app.add_handler(CallbackQueryHandler(verify_membership, pattern="^verify$"))

    # Text messages
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        lambda update, ctx: (
            handle_wiki(update, ctx) if ctx.user_data.get("awaiting_wiki") 
            else start(update, ctx)
        )
    ))

    # Start bot
    logger.info("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()