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

# ==================== IMPROVED CORE FUNCTIONS ==================== #
async def is_member(user_id: int, context: CallbackContext) -> bool:
    """Check if user is channel member with better error handling"""
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

# ==================== IMPROVED FEATURE HANDLERS ==================== #
async def handle_wiki(update: Update, context: CallbackContext) -> None:
    """Wikipedia search with proper state management"""
    if not await enforce_membership(update, context):
        return
    
    try:
        topic = update.message.text
        response = requests.get(f"{API_URLS['wiki']}{topic}", timeout=8)
        response.raise_for_status()  # Raise HTTP errors
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
    """Enhanced quiz with answer validation"""
    if not await enforce_membership(update, context):
        return
    
    try:
        # Store quiz data in user context
        response = requests.get(API_URLS["quiz"], timeout=5).json()
        question = response["results"][0]
        
        # Format options
        options = [question["correct_answer"]] + question["incorrect_answers"]
        random.shuffle(options)
        
        # Store correct answer for verification
        context.user_data['correct_answer'] = question["correct_answer"]
        
        # Create buttons for each option
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
    
    # Extract selected answer index
    selected_index = int(query.data.split('_')[-1])
    options = [button.text for row in query.message.reply_markup.inline_keyboard for button in row]
    selected_answer = options[selected_index]
    
    # Verify answer
    if selected_answer == context.user_data.get('correct_answer'):
        await query.edit_message_text(f"✅ Correct! The answer was:\n\n{selected_answer}")
    else:
        correct = context.user_data.get('correct_answer')
        await query.edit_message_text(f"❌ Wrong! The correct answer was:\n\n{correct}")

async def handle_weather(update: Update, context: CallbackContext) -> None:
    """Weather lookup with city validation"""
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
    """Currency converter with validation"""
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

# ==================== BOT SETUP ==================== #
def main() -> None:
    """Start the bot with all handlers"""
    # Validate tokens before starting
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
        lambda update, ctx: handle_quiz(update, ctx),
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
        lambda update, ctx: handle_fact(update, ctx),
        pattern="^fact$"
    ))
    application.add_handler(CallbackQueryHandler(
        lambda update, ctx: handle_joke(update, ctx),
        pattern="^joke$"
    ))
    application.add_handler(CallbackQueryHandler(
        lambda update, ctx: handle_word(update, ctx),
        pattern="^word$"
    ))
    application.add_handler(CallbackQueryHandler(
        lambda update, ctx: enforce_membership(update, ctx),
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
    
    logging.info("Bot starting with enforced channel membership...")
    application.run_polling()

if __name__ == "__main__":
    main()