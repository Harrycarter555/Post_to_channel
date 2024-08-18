import os
import requests
from flask import Flask, request, send_from_directory
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
import logging

app = Flask(__name__)

# Load configuration from environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
CHANNEL_ID = os.getenv('CHANNEL_ID')
TUTORIAL_LINK = os.getenv('TUTORIAL_LINK')

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable is not set.")
if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL environment variable is not set.")
if not CHANNEL_ID:
    raise ValueError("CHANNEL_ID environment variable is not set.")
if not TUTORIAL_LINK:
    raise ValueError("TUTORIAL_LINK environment variable is not set.")

# Initialize Telegram bot
bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0)

# Set up basic logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define states for the conversation
PHOTO, URL, FILE_NAME = range(3)

# Start command handler
def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("🖼️ Please upload a photo.")
    logger.info("Start command invoked")
    return PHOTO

# Receive photo handler
def receive_photo(update: Update, context: CallbackContext) -> int:
    photo = update.message.photo[-1]  # Get the highest resolution photo
    context.user_data['photo_file_id'] = photo.file_id
    update.message.reply_text("🔗 Please send a URL.")
    logger.info("Received photo: %s", photo.file_id)
    return URL

# Receive URL handler
def receive_url(update: Update, context: CallbackContext) -> int:
    context.user_data['url'] = update.message.text
    update.message.reply_text("📝 Please send the file name.")
    logger.info("Received URL: %s", update.message.text)
    return FILE_NAME

# Receive file name and post to channel
def receive_file_name(update: Update, context: CallbackContext) -> int:
    file_name = update.message.text
    url = context.user_data['url']
    photo_file_id = context.user_data['photo_file_id']

    # Post format preparation (HTML Text for bold and italic)
    post_text = f"""
    📂 File Name:
    <b>{file_name}</b>

    🌐 Link is here:
    {url}

    💡 How to Open (Tutorial):
    {TUTORIAL_LINK}

    🚀 Enjoy exploring the content!
    """
    
    try:
        # Log the message and request URL
        logger.info("Posting message to channel %s", CHANNEL_ID)
        logger.info("Message text: %s", post_text)
        
        # Post photo to channel
        context.bot.send_photo(chat_id=CHANNEL_ID, photo=photo_file_id, caption=post_text, parse_mode='HTML')
        
        # Log response from Telegram
        update.message.reply_text("✅ Your file has been posted to the channel!")
        logger.info("Message posted to channel %s", CHANNEL_ID)
        
    except Exception as e:
        # Log the error with more details
        error_message = f"Error posting message to channel {CHANNEL_ID}: {e}"
        update.message.reply_text(f"❌ {error_message}")
        logger.error(error_message, exc_info=True)
    
    return ConversationHandler.END

# Cancel command handler
def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('❌ Operation canceled.')
    logger.info("Operation canceled by user")
    return ConversationHandler.END

# Set up conversation handler
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        PHOTO: [MessageHandler(Filters.photo & ~Filters.command, receive_photo)],
        URL: [MessageHandler(Filters.text & ~Filters.command, receive_url)],
        FILE_NAME: [MessageHandler(Filters.text & ~Filters.command, receive_file_name)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)

# Add handlers to dispatcher
dispatcher.add_handler(conv_handler)

# Webhook route
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        dispatcher.process_update(update)
        logger.info("Webhook received update: %s", request.get_json(force=True))
        return 'ok', 200
    except Exception as e:
        logger.error("Error processing webhook update: %s", e, exc_info=True)
        return 'Internal Server Error', 500

# Home route
@app.route('/')
def home():
    return 'Hello, World!'

# Favicon route
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.getcwd(), 'favicon.ico')

# Webhook setup route
@app.route('/setwebhook', methods=['GET', 'POST'])
def setup_webhook():
    try:
        response = requests.post(
            f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook',
            data={'url': WEBHOOK_URL}
        )
        if response.json().get('ok'):
            logger.info("Webhook setup successful")
            return "Webhook setup ok"
        else:
            logger.error("Webhook setup failed: %s", response.json())
            return "Webhook setup failed"
    except Exception as e:
        logger.error("Error setting up webhook: %s", e, exc_info=True)
        return "Webhook setup failed"

if __name__ == '__main__':
    app.run(port=5000, debug=True)
