import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, filters
import requests

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration - REPLACE THESE WITH YOUR VALUES
CHANNEL_USERNAME = "@YourChannelUsername"
OWNER_ID = 1206054854  # Your Telegram user ID

import os
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # From Railway
WEATHER_KEY = os.getenv("WEATHER_API_KEY")        # From Railway

# API Endpoints
WIKI_API_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/"
QUIZ_API_URL = "https://opentdb.com/api.php?amount=1&type=multiple"
WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"
FACT_API_URL = "https://uselessfacts.jsph.pl/random.json?language=en"
JOKE_API_URL = "https://v2.jokeapi.dev/joke/Any"
WORD_API_URL = "https://random-word-api.herokuapp.com/word"
CURRENCY_API_URL = "https://api.exchangerate-api.com/v4/latest/USD"

async def is_member(update: Update, context: CallbackContext) -> bool:
    user_id = update.effective_user.id
    if user_id == OWNER_ID:
        return True
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Membership check error: {e}")
        return False

async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
        [InlineKeyboardButton("✅ Check Membership", callback_data="check_member")],
        [InlineKeyboardButton("📋 Show Menu", callback_data="show_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"🤖 Welcome to AI Knowledge Bot!\n\n"
        f"Join {CHANNEL_USERNAME} to access all features!",
        reply_markup=reply_markup
    )

async def show_menu(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    if not await is_member(update, context):
        await query.edit_message_text(
            "❌ Please join our channel first to use the bot!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
                [InlineKeyboardButton("✅ Check Membership", callback_data="check_member")]
            ])
        )
        return
    
    keyboard = [
        [InlineKeyboardButton("📖 Wikipedia", callback_data="wiki")],
        [InlineKeyboardButton("❓ Quiz", callback_data="quiz")],
        [InlineKeyboardButton("⛅ Weather", callback_data="weather")],
        [InlineKeyboardButton("💡 Fact", callback_data="fact")],
        [InlineKeyboardButton("😂 Joke", callback_data="joke")],
        [InlineKeyboardButton("📝 Word", callback_data="word")],
        [InlineKeyboardButton("💱 Currency", callback_data="currency")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="show_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("📋 Main Menu - Choose an option:", reply_markup=reply_markup)

async def menu_selection(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    option = query.data
    
    if not await is_member(update, context):
        await show_menu(update, context)
        return
    
    if option == "wiki":
        await query.edit_message_text(
            "🔍 Please enter a topic for Wikipedia search:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("↩️ Back to Menu", callback_data="show_menu")]
            ])
        )
        context.user_data['awaiting_wiki'] = True
    elif option == "weather":
        await query.edit_message_text(
            "🌍 Enter a city name for weather information:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("↩️ Back to Menu", callback_data="show_menu")]
            ])
        )
        context.user_data['awaiting_weather'] = True
    elif option == "currency":
        await query.edit_message_text(
            "💱 Enter a currency code (e.g., USD, EUR):",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("↩️ Back to Menu", callback_data="show_menu")]
            ])
        )
        context.user_data['awaiting_currency'] = True
    else:
        await handle_immediate_response(update, context, option)

async def handle_immediate_response(update: Update, context: CallbackContext, option: str) -> None:
    query = update.callback_query
    try:
        if option == "quiz":
            response = requests.get(QUIZ_API_URL).json()
            question = response['results'][0]['question']
            text = f"❓ Quiz Question:\n\n{question}"
        elif option == "fact":
            response = requests.get(FACT_API_URL).json()
            text = f"💡 Fun Fact:\n\n{response['text']}"
        elif option == "joke":
            response = requests.get(JOKE_API_URL).json()
            text = "😂 Joke:\n\n"
            if 'setup' in response:
                text += f"{response['setup']}\n{response['delivery']}"
            else:
                text += response['joke']
        elif option == "word":
            response = requests.get(WORD_API_URL).json()
            text = f"📝 Random Word:\n\n{response[0]}"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Get Another", callback_data=option)],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="show_menu")]
        ]
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error in {option} handler: {e}")
        await query.edit_message_text(
            "⚠️ Sorry, something went wrong. Please try again later.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Main Menu", callback_data="show_menu")]
            ])
        )

async def handle_message(update: Update, context: CallbackContext) -> None:
    if 'awaiting_wiki' in context.user_data:
        await handle_wiki(update, context)
    elif 'awaiting_weather' in context.user_data:
        await handle_weather(update, context)
    elif 'awaiting_currency' in context.user_data:
        await handle_currency(update, context)
    else:
        keyboard = [[InlineKeyboardButton("📋 Show Menu", callback_data="show_menu")]]
        await update.message.reply_text(
            "Please select an option from the menu:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_wiki(update: Update, context: CallbackContext) -> None:
    topic = update.message.text
    try:
        response = requests.get(WIKI_API_URL + topic)
        if response.status_code == 200:
            data = response.json()
            text = f"📖 {data['title']}:\n\n{data['extract']}"
        else:
            text = "⚠️ No information found for this topic."
    except Exception as e:
        logger.error(f"Wiki error: {e}")
        text = "⚠️ Error fetching Wikipedia data."
    
    keyboard = [
        [InlineKeyboardButton("🔍 New Search", callback_data="wiki")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="show_menu")]
    ]
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data.pop('awaiting_wiki', None)

async def handle_weather(update: Update, context: CallbackContext) -> None:
    city = update.message.text
    try:
        params = {'q': city, 'appid': WEATHER_API_KEY, 'units': 'metric'}
        response = requests.get(WEATHER_API_URL, params=params).json()
        if response.get('cod') == 200:
            weather = response['weather'][0]['description']
            temp = response['main']['temp']
            text = (
                f"⛅ Weather in {city}:\n\n"
                f"• Condition: {weather}\n"
                f"• Temperature: {temp}°C"
            )
        else:
            text = "⚠️ City not found. Try another name."
    except Exception as e:
        logger.error(f"Weather error: {e}")
        text = "⚠️ Error fetching weather data."
    
    keyboard = [
        [InlineKeyboardButton("🌦 New City", callback_data="weather")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="show_menu")]
    ]
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data.pop('awaiting_weather', None)

async def handle_currency(update: Update, context: CallbackContext) -> None:
    currency = update.message.text.upper()
    try:
        response = requests.get(CURRENCY_API_URL).json()
        if currency in response['rates']:
            rate = response['rates'][currency]
            text = f"💱 Exchange Rate:\n\n1 USD = {rate:.2f} {currency}"
        else:
            text = "⚠️ Invalid currency code. Try USD, EUR, JPY, etc."
    except Exception as e:
        logger.error(f"Currency error: {e}")
        text = "⚠️ Error fetching currency data."
    
    keyboard = [
        [InlineKeyboardButton("💱 New Currency", callback_data="currency")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="show_menu")]
    ]
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data.pop('awaiting_currency', None)

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(show_menu, pattern="^show_menu$"))
    application.add_handler(CallbackQueryHandler(menu_selection))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Error handler
    application.add_error_handler(lambda u, c: logger.error(c.error) if c.error else None)
    
    logger.info("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()