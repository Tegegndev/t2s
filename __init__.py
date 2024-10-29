from flask import Flask, request
from flask import render_template
import telebot
from config import BOT_TOKEN, CHAT_ID

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)
WEBHOOK_URL = 'https://telebots.alwaysdata.net/t2s/webhook'


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Howdy, how are you doing?")


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

