import os
import logging
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

# ==================== CONFIGURATION ==================== #
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
OWNER_ID = 1206054854  # Replace with your Telegram ID
CHANNEL_USERNAME = "@MemeAddictsDaily"  # Your Telegram channel

# API Endpoints
API_URLS = {
    "wiki": "https://en.wikipedia.org/api/rest_v1/page/summary/",
    "quiz": "https://opentdb.com/api.php?amount=1&type=multiple",
    "weather": "https://api.openweathermap.org/data/2.5/weather",
    "fact": "https://uselessfacts.jsph.pl/random.json?language=en",
    "joke": "https://v2.jokeapi.dev/joke/Any",
    "word": "https://random-word-api.herokuapp.com/word",
    "currency": "https://api.exchangerate-api.com/v4/latest/USD"
}

# ==================== CORE FUNCTIONS ==================== #
async def is_member(update: Update, context: CallbackContext) -> bool:
    """Check if user is channel member"""
    user_id = update.effective_user.id
    if user_id == OWNER_ID:
        return True
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logging.error(f"Membership check failed: {e}")
        return False

async def start(update: Update, context: CallbackContext) -> None:
    """Send interactive menu"""
    keyboard = [
        [InlineKeyboardButton("📖 Wikipedia", callback_data="wiki"),
         InlineKeyboardButton("❓ Quiz", callback_data="quiz")],
        [InlineKeyboardButton("⛅ Weather", callback_data="weather"),
         InlineKeyboardButton("💡 Fact", callback_data="fact")],
        [InlineKeyboardButton("😂 Joke", callback_data="joke"),
         InlineKeyboardButton("📝 Word", callback_data="word")],
        [InlineKeyboardButton("💱 Currency", callback_data="currency")]
    ]
    await update.message.reply_text(
        "🤖 Choose a feature:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================== FEATURE HANDLERS ==================== #
async def handle_wiki(update: Update, context: CallbackContext) -> None:
    """Wikipedia search"""
    try:
        topic = update.message.text
        response = requests.get(f"{API_URLS['wiki']}{topic}", timeout=8)
        data = response.json()
        await update.message.reply_text(
            f"📖 {data['title']}:\n\n{data['extract'][:1000]}..."
        )
    except Exception as e:
        await update.message.reply_text("🔍 Wikipedia unavailable. Try /fact")

async def handle_quiz(update: Update, context: CallbackContext) -> None:
    """Trivia quiz"""
    try:
        response = requests.get(API_URLS["quiz"], timeout=5).json()
        question = response["results"][0]
        await update.message.reply_text(
            f"❓ {question['question']}\n\n"
            f"A) {question['correct_answer']}\n"
            f"B) {question['incorrect_answers'][0]}"
        )
    except Exception as e:
        await update.message.reply_text("📝 Quiz API down. Try /word")

async def handle_weather(update: Update, context: CallbackContext) -> None:
    """Weather lookup"""
    try:
        city = update.message.text
        response = requests.get(
            API_URLS["weather"],
            params={"q": city, "appid": WEATHER_API_KEY, "units": "metric"},
            timeout=10
        )
        data = response.json()
        await update.message.reply_text(
            f"⛅ {city}:\n"
            f"• Temp: {data['main']['temp']}°C\n"
            f"• {data['weather'][0]['description']}"
        )
    except Exception as e:
        await update.message.reply_text("🌧 Weather service down")

async def handle_fact(update: Update, context: CallbackContext) -> None:
    """Random fact"""
    try:
        fact = requests.get(API_URLS["fact"], timeout=5).json()["text"]
        await update.message.reply_text(f"💡 Did you know?\n\n{fact}")
    except Exception as e:
        await update.message.reply_text("🤯 Fact machine broken. Try /joke")

async def handle_joke(update: Update, context: CallbackContext) -> None:
    """Random joke"""
    try:
        joke = requests.get(API_URLS["joke"], timeout=5).json()
        if joke["type"] == "twopart":
            await update.message.reply_text(
                f"😂 {joke['setup']}\n\n{joke['delivery']}"
            )
        else:
            await update.message.reply_text(f"😆 {joke['joke']}")
    except Exception as e:
        await update.message.reply_text("🤡 Joke service unavailable")

async def handle_word(update: Update, context: CallbackContext) -> None:
    """Random word"""
    try:
        word = requests.get(API_URLS["word"], timeout=5).json()[0]
        await update.message.reply_text(f"📝 Today's word:\n\n{word.upper()}")
    except Exception as e:
        await update.message.reply_text("📚 Dictionary offline")

async def handle_currency(update: Update, context: CallbackContext) -> None:
    """Currency converter"""
    try:
        currency = update.message.text.upper()
        rates = requests.get(API_URLS["currency"], timeout=5).json()["rates"]
        await update.message.reply_text(
            f"💱 1 USD = {rates.get(currency, '?')} {currency}"
        )
    except Exception as e:
        await update.message.reply_text("💸 Currency service down")

# ==================== BOT SETUP ==================== #
def main() -> None:
    """Start the bot with all handlers"""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    
    # Callback handlers for menu
    application.add_handler(CallbackQueryHandler(
        lambda update, context: (
            context.user_data.update({"awaiting_wiki": True}),
            update.callback_query.message.reply_text("🔍 Enter a Wikipedia topic:")
        ),
        pattern="^wiki$"
    ))
    application.add_handler(CallbackQueryHandler(
        lambda update, context: (
            context.user_data.update({"awaiting_weather": True}),
            update.callback_query.message.reply_text("🌍 Enter a city name:")
        ),
        pattern="^weather$"
    ))
    application.add_handler(CallbackQueryHandler(
        lambda update, context: (
            context.user_data.update({"awaiting_currency": True}),
            update.callback_query.message.reply_text("💱 Enter currency code (e.g. USD):")
        ),
        pattern="^currency$"
    ))
    application.add_handler(CallbackQueryHandler(
        lambda update, context: handle_quiz(update.callback_query, context),
        pattern="^quiz$"
    ))
    application.add_handler(CallbackQueryHandler(
        lambda update, context: handle_fact(update.callback_query, context),
        pattern="^fact$"
    ))
    application.add_handler(CallbackQueryHandler(
        lambda update, context: handle_joke(update.callback_query, context),
        pattern="^joke$"
    ))
    application.add_handler(CallbackQueryHandler(
        lambda update, context: handle_word(update.callback_query, context),
        pattern="^word$"
    ))
    
    # Message handlers for text input
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        lambda update, context: (
            handle_wiki(update, context) if context.user_data.get("awaiting_wiki") else
            handle_weather(update, context) if context.user_data.get("awaiting_weather") else
            handle_currency(update, context) if context.user_data.get("awaiting_currency") else
            start(update, context)
        )
    ))
    
    # Error handling
    application.add_error_handler(
        lambda update, context: logging.error(f"Error: {context.error}", exc_info=True)
    )
    
    logging.info("Bot started successfully")
    application.run_polling()

if __name__ == "__main__":
    main()