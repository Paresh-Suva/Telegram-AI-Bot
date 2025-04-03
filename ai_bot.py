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

# ==================== CORE FUNCTIONS ==================== #
async def is_member(user_id: int, context: CallbackContext) -> bool:
    """Check if user is channel member"""
    if user_id == OWNER_ID:
        return True
    
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logging.error(f"Membership check failed: {e}")
        return False

async def enforce_membership(update: Update, context: CallbackContext):
    """Force users to join channel before using any features"""
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
    """Wikipedia search handler"""
    if not await enforce_membership(update, context):
        return
    
    try:
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
        logging.error(f"Wiki error: {e}")
        await update.message.reply_text("🔍 Wikipedia service unavailable. Try /fact")

async def handle_quiz(update: Update, context: CallbackContext) -> None:
    """Quiz handler"""
    if not await enforce_membership(update, context):
        return
    
    try:
        response = requests.get(API_URLS["quiz"], timeout=5).json()
        question = response["results"][0]
        
        options = [question["correct_answer"]] + question["incorrect_answers"]
        random.shuffle(options)
        
        context.user_data['correct_answer'] = question["correct_answer"]
        
        keyboard = [
            [InlineKeyboardButton(option, callback_data=f"quiz_answer_{i}")]
            for i, option in enumerate(options)
        ]
        
        await update.message.reply_text(
            f"❓ {question['question']}\n\n"
            "Choose your answer:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logging.error(f"Quiz error: {e}")
        await update.message.reply_text("📝 Quiz service down. Try /word")

async def handle_quiz_answer(update: Update, context: CallbackContext) -> None:
    """Check quiz answers"""
    query = update.callback_query
    await query.answer()
    
    selected_index = int(query.data.split('_')[-1])
    options = [button.text for row in query.message.reply_markup.inline_keyboard for button in row]
    selected_answer = options[selected_index]
    
    if selected_answer == context.user_data.get('correct_answer'):
        await query.edit_message_text(f"✅ Correct! The answer was:\n\n{selected_answer}")
    else:
        correct = context.user_data.get('correct_answer')
        await query.edit_message_text(f"❌ Wrong! The correct answer was:\n\n{correct}")

async def handle_weather(update: Update, context: CallbackContext) -> None:
    """Weather lookup handler"""
    if not await enforce_membership(update, context):
        return
    
    try:
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
        
        if data.get('cod') != 200:
            await update.message.reply_text("🌍 City not found. Try again with correct spelling.")
            return
            
        weather = (
            f"⛅ Weather in {data['name']}:\n\n"
            f"• Temperature: {data['main']['temp']}°C\n"
            f"• Feels like: {data['main']['feels_like']}°C\n"
            f"• Conditions: {data['weather'][0]['description'].capitalize()}\n"
            f"• Humidity: {data['main']['humidity']}%\n"
            f"• Wind: {data['wind']['speed']} m/s"
        )
        await update.message.reply_text(weather)
        
    except requests.exceptions.Timeout:
        await update.message.reply_text("⌛ Weather service timeout. Try again later.")
    except Exception as e:
        logging.error(f"Weather error: {e}")
        await update.message.reply_text("🌧 Weather service unavailable. Try /wiki")

async def handle_currency(update: Update, context: CallbackContext) -> None:
    """Currency converter handler"""
    if not await enforce_membership(update, context):
        return
    
    try:
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
        logging.error(f"Currency error: {e}")
        await update.message.reply_text("💸 Currency service down. Try /fact")

async def handle_fact(update: Update, context: CallbackContext) -> None:
    """Random fact handler"""
    if not await enforce_membership(update, context):
        return
    
    try:
        response = requests.get(API_URLS["fact"], timeout=5)
        response.raise_for_status()
        data = response.json()
        await update.message.reply_text(f"📚 Did you know?\n\n{data['text']}")
    except Exception as e:
        logging.error(f"Fact error: {e}")
        await update.message.reply_text("📖 Fact service unavailable. Try /joke")

async def handle_joke(update: Update, context: CallbackContext) -> None:
    """Random joke handler"""
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
        logging.error(f"Joke error: {e}")
        await update.message.reply_text("😅 Joke service down. Try /fact")

async def handle_word(update: Update, context: CallbackContext) -> None:
    """Random word handler"""
    if not await enforce_membership(update, context):
        return
    
    try:
        response = requests.get(API_URLS["word"], timeout=5)
        response.raise_for_status()
        word = response.json()[0]
        await update.message.reply_text(f"📖 Your random word:\n\n{word.capitalize()}")
    except Exception as e:
        logging.error(f"Word error: {e}")
        await update.message.reply_text("📚 Word service unavailable. Try /wiki")

async def verify_membership(update: Update, context: CallbackContext) -> None:
    """Verify channel membership"""
    query = update.callback_query
    await query.answer()
    
    if await is_member(query.from_user.id, context):
        await query.edit_message_text("✅ Thanks for joining! You can now use all bot features.")
    else:
        await query.edit_message_text("❌ You haven't joined the channel yet. Please join and try again.")

# ==================== BOT SETUP ==================== #
def main() -> None:
    """Start the bot"""
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable missing!")
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(
        lambda update, ctx: (
            ctx.user_data.update({"awaiting_wiki": True}),
            update.callback_query.message.reply_text("🔍 Enter a Wikipedia topic:")
        ),
        pattern="^wiki$"
    ))
    application.add_handler(CallbackQueryHandler(
        handle_quiz,
        pattern="^quiz$"
    ))
    application.add_handler(CallbackQueryHandler(
        lambda update, ctx: (
            ctx.user_data.update({"awaiting_weather": True}),
            update.callback_query.message.reply_text("🌍 Enter a city name:")
        ),
        pattern="^weather$"
    ))
    application.add_handler(CallbackQueryHandler(
        lambda update, ctx: (
            ctx.user_data.update({"awaiting_currency": True}),
            update.callback_query.message.reply_text("💱 Enter currency code (e.g. USD):")
        ),
        pattern="^currency$"
    ))
    application.add_handler(CallbackQueryHandler(
        handle_quiz_answer,
        pattern="^quiz_answer_"
    ))
    application.add_handler(CallbackQueryHandler(
        handle_fact,
        pattern="^fact$"
    ))
    application.add_handler(CallbackQueryHandler(
        handle_joke,
        pattern="^joke$"
    ))
    application.add_handler(CallbackQueryHandler(
        handle_word,
        pattern="^word$"
    ))
    application.add_handler(CallbackQueryHandler(
        verify_membership,
        pattern="^verify_membership$"
    ))
    
    # Message handlers
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        lambda update, ctx: (
            handle_wiki(update, ctx) if ctx.user_data.get("awaiting_wiki") else
            handle_weather(update, ctx) if ctx.user_data.get("awaiting_weather") else
            handle_currency(update, ctx) if ctx.user_data.get("awaiting_currency") else
            start(update, ctx)
        )
    ))
    
    # Error handling
    application.add_error_handler(
        lambda update, ctx: logging.error(f"Error: {ctx.error}", exc_info=True)
    )
    
    logging.info("Bot starting...")
    application.run_polling()

if __name__ == "__main__":
    main()