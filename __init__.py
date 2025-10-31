from flask import Flask, request
from flask import render_template
import telebot
from config import BOT_TOKEN, CHAT_ID, DETECT_LANG_API_KEY, TEXT_TO_SPEECH_API_URL
import detectlanguage
import requests
from telebot import types
import json
import os

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)
WEBHOOK_URL = 'https://telebots.alwaysdata.net/t2s/webhook'

# Initialize detectlanguage configuration once
detectlanguage.configuration.api_key = DETECT_LANG_API_KEY
detectlanguage.configuration.secure = True

# Cache for user data to avoid repeated file reads
_user_cache = None

def _load_user_cache():
    """Load user data into memory cache once"""
    global _user_cache
    if _user_cache is not None:
        return _user_cache
    
    _user_cache = set()
    if os.path.exists('user_data.json'):
        try:
            with open('user_data.json', 'r') as file:
                for line in file:
                    if line.strip():
                        user = json.loads(line)
                        _user_cache.add(user['user_id'])
        except (json.JSONDecodeError, KeyError):
            pass
    return _user_cache


def store_user_data(user_id, username):
    """Store user data efficiently using in-memory cache"""
    user_cache = _load_user_cache()
    
    # Check if user already exists in cache
    if user_id in user_cache:
        return True
    
    # Add to cache and append to file
    user_cache.add(user_id)
    try:
        with open('user_data.json', 'a') as file:
            json.dump({'user_id': user_id, 'username': username}, file)
            file.write('\n')
        return True
    except IOError:
        # Remove from cache if file write fails
        user_cache.discard(user_id)
        return False


class TextToSpeechApi:
    _instance = None
    
    def __new__(cls):
        """Implement singleton pattern to avoid repeated initialization"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
            cls._instance._language_cache = {}
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

    def detect_language(self, text):
        """Detect language with caching for frequently used texts"""
        # Limit text length to prevent memory issues from malicious input
        cache_key = text[:500] if len(text) > 500 else text
        
        # Check cache first
        if cache_key in self._language_cache:
            return self._language_cache[cache_key]
        
        try:
            lang = detectlanguage.simple_detect(text)
            # Cache the result (limit cache size to prevent memory issues)
            if len(self._language_cache) >= 128:
                # Remove oldest entry (FIFO - dict maintains insertion order in Python 3.7+)
                first_key = next(iter(self._language_cache))
                del self._language_cache[first_key]
            self._language_cache[cache_key] = lang
            return lang
        except Exception as e:
            raise Exception(f"Language detection failed: {str(e)}")
    
    def text_to_speech(self, text, filename):
        try:
            # Ensure voices directory exists
            os.makedirs('./voices', exist_ok=True)
            
            url = TEXT_TO_SPEECH_API_URL
            lang = self.detect_language(text)
            params = {
                "text": text,
                "lang": lang
            }
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()  # Raises an HTTPError for bad responses
            
            audio_file = f"./voices/{filename}.mp3"
            with open(audio_file, 'wb') as f:
                f.write(response.content)
            return audio_file
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")
        except IOError as e:
            raise Exception(f"File operation failed: {str(e)}")


@bot.message_handler(commands=['start'])
def start(message):
    keyboard = types.InlineKeyboardMarkup()
    help = types.InlineKeyboardButton("🆘 Help", callback_data='help')
    about = types.InlineKeyboardButton("👥 About", callback_data='about')
    keyboard.add(help, about)
    channel = types.InlineKeyboardButton("👥 Channel", url='https://t.me/tegegndev')
    keyboard.add(channel)
    developer = types.InlineKeyboardButton("👨‍💻 Developer", url='https://t.me/yegna_tv')
    keyboard.add(developer)
    bot.send_message(message.chat.id, "👋Welcome to Text-to-Speech Bot! 🎙️\n\n"
                     "I can convert any text you send me into speech. 🗣️\n\n"
                     "Just send me some text and I'll convert it to audio for you! 🔊\n\n"
                     , reply_markup=keyboard)

#handle all user messages
@bot.message_handler(func=lambda message: True)
def message_handler(message):
    if message.text and not message.text.startswith('/'):
        if len(message.text) > 1000:
            bot.send_message(message.chat.id, "Please send a text less than 1000 characters")
        else:
            process_text(message)
    else:
        bot.send_message(message.chat.id, "Please send a text message")

# Callback function to handle language selection
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == 'help':
        bot.answer_callback_query(call.id)
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "Text-to-Speech Bot! 🎙️\n\n"
                     "I can convert any text you send me into speech. 🗣️\n\n"
                     "Just send me some text and I'll convert it to audio for you! 🔊\n\n"
                     "if you want to suggest a feature or report a bug, please contact @yegna_tv")
    elif call.data == 'about':
        bot.answer_callback_query(call.id)
        bot.delete_message(call.message.chat.id, call.message.message_id)
        channel = types.InlineKeyboardButton("👥 Channel", url='https://t.me/tegegndev')
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(channel)
        bot.send_message(call.message.chat.id, "This bot is developed by @yegna_tv. \nJoin channel to get updates about the bot.", reply_markup=keyboard)

def process_text(message):
    user_id = message.chat.id
    msg = None
    audio_file = None
    try:
        msg = bot.send_message(user_id, "Processing your text...")
        api = TextToSpeechApi()
        
        audio_file = api.text_to_speech(message.text, f'@{bot.get_me().username}_{user_id}')
        
        with open(audio_file, "rb") as audio:
            bot.send_audio(message.chat.id, audio)
        
        # Delete the processing message after successful completion
        if msg:
            try:
                bot.delete_message(user_id, msg.message_id)
            except Exception:
                # Ignore errors when deleting message (e.g., already deleted, permissions)
                pass
                
    except Exception as e:
        bot.send_message(message.chat.id, f"Sorry, an error occurred while processing your request. Please try again later.")
    finally:
        # Cleanup the audio file after sending
        if audio_file and os.path.exists(audio_file):
            try:
                os.remove(audio_file)
            except OSError:
                pass


@app.route('/')
def hello_world():
    return "Git is awesome i liked it"

# Webhook endpoint to handle incoming updates
@app.route('/webhook', methods=['POST'])
def webhook():
    json_data = request.get_json()
    bot.process_new_updates([telebot.types.Update.de_json(json_data)])
    return '', 200

# Set the webhook
@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    if bot.set_webhook(WEBHOOK_URL):
        return "Webhook set successfully!", 200
    else:
        return "Failed to set webhook.", 400
    


if __name__ == "__main__":
  app.run(debug=True)

