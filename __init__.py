from flask import Flask
from flask import render_template
import telebot
from config import BOT_TOKEN, CHAT_ID

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)

@app.route('/')
def hello_world():
    return "Git is awesome i liked it"

@app.route('/hello')    
def hello():
    bot.send_message(CHAT_ID, "Hello, World!")
    return "message sent!"

if __name__ == "__main__":
  app.run(debug=True)

