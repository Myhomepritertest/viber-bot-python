from flask import Flask, request, Response
from viberbot import Api
from viberbot.api.bot_configuration import BotConfiguration
from viberbot.api.messages.text_message import TextMessage
from viberbot.api.viber_requests import ViberMessageRequest

import time
import logging
import sched
import threading
import os
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Logging setup
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Flask & Viber setup
app = Flask(__name__)
viber = Api(BotConfiguration(
    name='PythonSampleBot',
    avatar='http://viber.com/avatar.jpg',
    auth_token=os.environ['VIBER_AUTH_TOKEN']
))

app.logger.debug(">>> VIBER_AUTH_TOKEN φορτώθηκε ως: %s", os.environ.get("VIBER_AUTH_TOKEN"))

# Google Sheets setup
def get_sheet():
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]
    creds_path = os.getenv("GOOGLE_CREDS_PATH", "/etc/secrets/viber-bot-writer-15e183a8df85.json")
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    client = gspread.authorize(creds)
    sheet = client.open("Παραγγελίες").sheet1  # Το όνομα του spreadsheet σου
    return sheet

def save_order_to_sheet(user_id, order):
    try:
        sheet = get_sheet()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([user_id, order, now])
        print("✅ Order saved to Google Sheets")
    except Exception as e:
        print("❌ Error writing to sheet:", e)

# 🍽 Custom Keyboard με 4 φαγητά
food_keyboard = {
    "Type": "keyboard",
    "DefaultHeight": True,
    "Buttons": [
        {"Columns": 3, "Rows": 1, "Text": "🍔 Burger", "ActionType": "reply", "ActionBody": "burger"},
        {"Columns": 3, "Rows": 1, "Text": "🍕 Pizza", "ActionType": "reply", "ActionBody": "pizza"},
        {"Columns": 3, "Rows": 1, "Text": "🥗 Σαλάτα", "ActionType": "reply", "ActionBody": "salad"},
        {"Columns": 3, "Rows": 1, "Text": "🍟 Πατάτες", "ActionType": "reply", "ActionBody": "fries"}
    ]
}

@app.route('/', methods=['POST'])
def incoming():
    viber_request = viber.parse_request(request.get_data())

    if isinstance(viber_request, ViberMessageRequest):
        user_text = viber_request.message.text.strip().lower()

        if user_text == '/start':
            viber.send_messages(viber_request.sender.id, [
                TextMessage(text="🍽 Τι θα ήθελες να παραγγείλεις;", keyboard=food_keyboard)
            ])

        elif user_text == 'burger':
            save_order_to_sheet(viber_request.sender.id, "Burger")
            viber.send_messages(viber_request.sender.id, [
                TextMessage(text="🍔 Επιλέχθηκε Burger. Η παραγγελία σου καταχωρήθηκε!")
            ])

        elif user_text == 'pizza':
            save_order_to_sheet(viber_request.sender.id, "Pizza")
            viber.send_messages(viber_request.sender.id, [
                TextMessage(text="🍕 Επιλέχθηκε Pizza. Η παραγγελία σου καταχωρήθηκε!")
            ])

        elif user_text == 'salad':
            save_order_to_sheet(viber_request.sender.id, "Salad")
            viber.send_messages(viber_request.sender.id, [
                TextMessage(text="🥗 Επιλέχθηκε Σαλάτα. Η παραγγελία σου καταχωρήθηκε!")
            ])

        elif user_text == 'fries':
            save_order_to_sheet(viber_request.sender.id, "Fries")
            viber.send_messages(viber_request.sender.id, [
                TextMessage(text="🍟 Επιλέχθηκαν Πατάτες. Η παραγγελία σου καταχωρήθηκε!")
            ])

        else:
            viber.send_messages(viber_request.sender.id, [
                TextMessage(text="❓ Δεν κατάλαβα. Γράψε `/start` για να ξεκινήσεις νέα παραγγελία.")
            ])

    return Response(status=200)

# 🔗 Set webhook (τρέχει στην αρχή)
def set_webhook(viber):
    viber.set_webhook('https://your-bot-url.onrender.com/')  # Άλλαξε το URL με το δικό σου!

if __name__ == "__main__":
    scheduler = sched.scheduler(time.time, time.sleep)
    scheduler.enter(5, 1, set_webhook, (viber,))
    t = threading.Thread(target=scheduler.run)
    t.start()

    # Για local με SSL (χρήσιμο σε dev)
    context = ('server.crt', 'server.key')  # αν έχεις πιστοποιητικό
    app.run(host='0.0.0.0', port=8443, debug=True, ssl_context=context)
