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

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== CORE FUNCTIONS ==================== #
async def is_member(user_id: int, context: CallbackContext) -> bool:
    """Check if user is channel member"""
    if user_id == OWNER_ID:
        return True
    
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Membership check failed: {e}")
        return False

async def enforce_membership(update: Update, context: CallbackContext):
    """Force users to join channel before using features"""
    user_id = update.effective_user.id
    if not await is_member(user_id, context):
        keyboard = [
            [InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("✅ Verify Membership", callback_data="verify_membership")]
        ]
        await update.message.reply_text(
            "🔒 Please join our channel first to use this bot:\n\n"
            f"{CHANNEL_USERNAME}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return False
    return True

# ==================== HANDLER FUNCTIONS ==================== #
async def start(update: Update, context: CallbackContext) -> None:
    """Send welcome message and main menu"""
    welcome_text = (
        "🌟 Welcome to Multi-Feature Bot! 🌟\n\n"
        "I can help with:\n"
        "• Wikipedia searches (/wiki)\n"
        "• Quizzes (/quiz)\n"
        "• Weather (/weather)\n"
        "• Currency rates (/currency)\n"
        "• Random facts (/fact)\n"
        "• Jokes (/joke)\n"
        "• Random words (/word)\n\n"
        "Just send me a command!"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔍 Wikipedia", callback_data="wiki"),
         InlineKeyboardButton("❓ Quiz", callback_data="quiz")],
        [InlineKeyboardButton("⛅ Weather", callback_data="weather"),
         InlineKeyboardButton("💱 Currency", callback_data="currency")],
        [InlineKeyboardButton("📚 Random Fact", callback_data="fact"),
         InlineKeyboardButton("😂 Joke", callback_data="joke")],
        [InlineKeyboardButton("📖 Random Word", callback_data="word")]
    ]
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_wiki(update: Update, context: CallbackContext) -> None:
    """Handle Wikipedia requests"""
    if not await enforce_membership(update, context):
        return
    
    try:
        # Clear previous state
        context.user_data.pop("awaiting_wiki", None)
        
        if update.message.text == '/wiki':
            context.user_data["awaiting_wiki"] = True
            await update.message.reply_text("🔍 Enter a Wikipedia topic:")
            return

        topic = update.message.text
        response = requests.get(f"{API_URLS['wiki']}{topic}", timeout=8)
        response.raise_for_status()
        data = response.json()
        
        if 'extract' not in data:
            await update.message.reply_text("📚 No summary found. Try different keywords.")
            return
            
        await update.message.reply_text(
            f"📖 {data['title']}:\n\n{data['extract'][:1000]}...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 New Search", callback_data="wiki")]
            ])
        )
    except Exception as e:
        logger.error(f"Wiki error: {e}")
        await update.message.reply_text("🔍 Wikipedia service unavailable. Try /fact")

async def handle_quiz(update: Update, context: CallbackContext) -> None:
    """Handle quiz requests"""
    if not await enforce_membership(update, context):
        return
    
    try:
        response = requests.get(API_URLS["quiz"], timeout=5).json()
        question = response["results"][0]
        
        options = question["incorrect_answers"] + [question["correct_answer"]]
        random.shuffle(options)
        
        context.user_data['correct_answer'] = question["correct_answer"]
        
        keyboard = [
            [InlineKeyboardButton(option, callback_data=f"quiz_{i}")]
            for i, option in enumerate(options)
        ]
        
        await update.message.reply_text(
            f"❓ {question['question']}\n\n"
            "Choose your answer:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Quiz error: {e}")
        await update.message.reply_text("📝 Quiz service down. Try /word")

async def handle_quiz_answer(update: Update, context: CallbackContext) -> None:
    """Handle quiz answers"""
    query = update.callback_query
    await query.answer()
    
    try:
        selected_index = int(query.data.split('_')[-1])
        options = [button.text for row in query.message.reply_markup.inline_keyboard for button in row]
        selected_answer = options[selected_index]
        correct = context.user_data.get('correct_answer')
        
        if selected_answer == correct:
            await query.edit_message_text(f"✅ Correct! The answer was:\n{correct}")
        else:
            await query.edit_message_text(f"❌ Wrong! Correct answer was:\n{correct}")
            
    except Exception as e:
        logger.error(f"Quiz answer error: {e}")
        await query.edit_message_text("⚠️ Error processing answer")

async def handle_weather(update: Update, context: CallbackContext) -> None:
    """Handle weather requests"""
    if not await enforce_membership(update, context):
        return
    
    try:
        if update.message.text == '/weather':
            context.user_data["awaiting_weather"] = True
            await update.message.reply_text("🌍 Enter a city name:")
            return

        city = update.message.text
        response = requests.get(
            API_URLS["weather"],
            params={
                "q": city,
                "appid": WEATHER_API_KEY,
                "units": "metric",
                "lang": "en"
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        weather = (
            f"⛅ Weather in {data['name']}:\n\n"
            f"• Temperature: {data['main']['temp']}°C\n"
            f"• Feels like: {data['main']['feels_like']}°C\n"
            f"• Conditions: {data['weather'][0]['description'].capitalize()}\n"
            f"• Humidity: {data['main']['humidity']}%\n"
            f"• Wind: {data['wind']['speed']} m/s"
        )
        await update.message.reply_text(weather)
        
    except requests.exceptions.HTTPError as e:
        await update.message.reply_text("🌍 City not found. Try again with correct spelling.")
    except Exception as e:
        logger.error(f"Weather error: {e}")
        await update.message.reply_text("🌧 Weather service unavailable. Try /wiki")

async def handle_currency(update: Update, context: CallbackContext) -> None:
    """Handle currency requests"""
    if not await enforce_membership(update, context):
        return
    
    try:
        if update.message.text == '/currency':
            context.user_data["awaiting_currency"] = True
            await update.message.reply_text("💱 Enter currency code (e.g. EUR):")
            return

        currency = update.message.text.upper()
        response = requests.get(API_URLS["currency"], timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if currency not in data['rates']:
            await update.message.reply_text(
                "💱 Invalid currency code. Examples:\n"
                "USD, EUR, GBP, JPY, INR\n"
                "See full list: https://www.exchangerate-api.com/docs/supported-currencies"
            )
            return
            
        rate = data['rates'][currency]
        await update.message.reply_text(
            f"💱 Exchange Rates:\n\n"
            f"1 USD = {rate:.2f} {currency}\n"
            f"1 {currency} = {1/rate:.4f} USD"
        )
        
    except Exception as e:
        logger.error(f"Currency error: {e}")
        await update.message.reply_text("💸 Currency service down. Try /fact")

async def handle_fact(update: Update, context: CallbackContext) -> None:
    """Handle random facts"""
    if not await enforce_membership(update, context):
        return
    
    try:
        response = requests.get(API_URLS["fact"], timeout=5)
        response.raise_for_status()
        data = response.json()
        await update.message.reply_text(f"📚 Did you know?\n\n{data['text']}")
    except Exception as e:
        logger.error(f"Fact error: {e}")
        await update.message.reply_text("📖 Fact service unavailable. Try /joke")

async def handle_joke(update: Update, context: CallbackContext) -> None:
    """Handle jokes"""
    if not await enforce_membership(update, context):
        return
    
    try:
        response = requests.get(API_URLS["joke"], timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data['type'] == 'twopart':
            joke = f"{data['setup']}\n\n...{data['delivery']}"
        else:
            joke = data['joke']
            
        await update.message.reply_text(f"😂 Joke:\n\n{joke}")
    except Exception as e:
        logger.error(f"Joke error: {e}")
        await update.message.reply_text("😅 Joke service down. Try /fact")

async def handle_word(update: Update, context: CallbackContext) -> None:
    """Handle random words"""
    if not await enforce_membership(update, context):
        return
    
    try:
        response = requests.get(API_URLS["word"], timeout=5)
        response.raise_for_status()
        word = response.json()[0]
        await update.message.reply_text(f"📖 Your random word:\n\n{word.capitalize()}")
    except Exception as e:
        logger.error(f"Word error: {e}")
        await update.message.reply_text("📚 Word service unavailable. Try /wiki")

async def verify_membership(update: Update, context: CallbackContext) -> None:
    """Verify channel membership"""
    query = update.callback_query
    await query.answer()
    
    try:
        if await is_member(query.from_user.id, context):
            await query.edit_message_text("✅ Thanks for joining! You can now use all bot features.")
        else:
            await query.edit_message_text("❌ You haven't joined the channel yet. Please join and try again.")
    except Exception as e:
        logger.error(f"Membership verification error: {e}")
        await query.edit_message_text("⚠️ Error verifying membership")

# ==================== BOT SETUP ==================== #
def main() -> None:
    """Start the bot"""
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable missing!")
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Command handlers
    command_handlers = [
        CommandHandler("start", start),
        CommandHandler("wiki", handle_wiki),
        CommandHandler("quiz", handle_quiz),
        CommandHandler("weather", handle_weather),
        CommandHandler("currency", handle_currency),
        CommandHandler("fact", handle_fact),
        CommandHandler("joke", handle_joke),
        CommandHandler("word", handle_word)
    ]
    
    # Callback handlers
    callback_handlers = [
        CallbackQueryHandler(handle_wiki, pattern="^wiki$"),
        CallbackQueryHandler(handle_quiz, pattern="^quiz$"),
        CallbackQueryHandler(handle_weather, pattern="^weather$"),
        CallbackQueryHandler(handle_currency, pattern="^currency$"),
        CallbackQueryHandler(handle_quiz_answer, pattern=r"^quiz_"),
        CallbackQueryHandler(handle_fact, pattern="^fact$"),
        CallbackQueryHandler(handle_joke, pattern="^joke$"),
        CallbackQueryHandler(handle_word, pattern="^word$"),
        CallbackQueryHandler(verify_membership, pattern="^verify_membership$")
    ]
    
    # Message handler
    async def handle_messages(update: Update, context: CallbackContext):
        if context.user_data.get("awaiting_wiki"):
            await handle_wiki(update, context)
        elif context.user_data.get("awaiting_weather"):
            await handle_weather(update, context)
        elif context.user_data.get("awaiting_currency"):
            await handle_currency(update, context)
        else:
            await start(update, context)
    
    message_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages)
    
    # Add all handlers
    application.add_handlers(command_handlers + callback_handlers)
    application.add_handler(message_handler)
    
    # Error handling
    application.add_error_handler(lambda update, ctx: logger.error(f"Error: {ctx.error}", exc_info=True))
    
    logger.info("Bot starting...")
    application.run_polling()

if __name__ == "__main__":
    main()