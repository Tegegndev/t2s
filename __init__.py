from flask import Flask, request
from flask import render_template
import telebot
from config import BOT_TOKEN, CHAT_ID, DETECT_LANG_API_KEY, TEXT_TO_SPEECH_API_URL
import detectlanguage
import requests
from telebot import types

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)
WEBHOOK_URL = 'https://telebots.alwaysdata.net/t2s/webhook'
detectlanguage.configuration.secure = True

class TextToSpeechApi:
    def __init__(self):
        self.detectlanguage = detectlanguage
        self.detectlanguage.configuration.api_key = DETECT_LANG_API_KEY
        self.detectlanguage.configuration.secure = True

    def detect_language(self, text):
        try:
            return self.detectlanguage.simple_detect(text)
        except Exception as e:
            raise Exception(f"Language detection failed: {str(e)}")
    
    def text_to_speech(self, text, filename):
        try:
            url = TEXT_TO_SPEECH_API_URL
            lang = self.detect_language(text)
            params = {
                "text": text,
                "lang": lang
            }
            response = requests.get(url, params=params)
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
''' try:
        store_user_data(message.from_user.id, message.from_user.username)
    except Exception as e:
        pass
'''

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
    try:
        msg = bot.send_message(user_id, "Processing your text...")
        api = TextToSpeechApi()
        
        audio_file = api.text_to_speech(message.text, user_id)
        
        with open(audio_file, "rb") as audio:
            bot.send_audio(message.chat.id, audio)
            
        # Cleanup the audio file after sending
        import os
        os.remove(audio_file)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"Sorry, an error occurred while processing your request. Please try again later.")


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

