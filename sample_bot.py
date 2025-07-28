from flask import Flask, request, Response
from viberbot import Api
from viberbot.api.bot_configuration import BotConfiguration
from viberbot.api.messages.text_message import TextMessage
from viberbot.api.messages.keyboard_message import KeyboardMessage
from viberbot.api.viber_requests import ViberMessageRequest
import time
import logging
import sched
import threading
import os
import datetime
import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

app = Flask(__name__)
viber = Api(BotConfiguration(
    name='PythonSampleBot',
    avatar='http://viber.com/avatar.jpg',
    auth_token=os.environ['VIBER_AUTH_TOKEN']
))

# Keyboard με φαγητά
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

# Keyboard με επιβεβαίωση Ναι/Όχι
confirm_keyboard = {
    "Type": "keyboard",
    "DefaultHeight": True,
    "Buttons": [
        {"Columns": 3, "Rows": 1, "Text": "✅ Ναι", "ActionType": "reply", "ActionBody": "confirm_yes"},
        {"Columns": 3, "Rows": 1, "Text": "❌ Όχι", "ActionType": "reply", "ActionBody": "confirm_no"}
    ]
}

# Google Sheets setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
CREDS_PATH = os.environ.get('GOOGLE_CREDS_PATH', '/etc/secrets/viber-bot-writer-15e183a8df85.json')

def get_sheet():
    creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open("Παραγγελίες").sheet1
    return sheet

# Για να κρατάμε το στάδιο της παραγγελίας για κάθε χρήστη
user_sessions = {}

def save_order_to_sheet(user_id, food, quantity):
    try:
        sheet = get_sheet()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([now, user_id, food, quantity])
        logger.info(f"Saved order: {food} x {quantity} for user {user_id}")
    except Exception as e:
        logger.error(f"Error writing to sheet: {e}")

@app.route('/', methods=['POST'])
def incoming():
    viber_request = viber.parse_request(request.get_data())

    if isinstance(viber_request, ViberMessageRequest):
        user_id = viber_request.sender.id
        user_text = viber_request.message.text.strip().lower()

        # Έλεγχος αν ο χρήστης έχει ήδη επιλέξει φαγητό και περιμένουμε ποσότητα
        if user_id in user_sessions:
            session = user_sessions[user_id]

            if session.get('waiting_quantity'):
                # Εδώ περιμένουμε ποσότητα
                if user_text.isdigit() and int(user_text) > 0:
                    quantity = int(user_text)
                    food = session['food']

                    # Αποθήκευση παραγγελίας
                    save_order_to_sheet(user_id, food, quantity)

                    # Καθαρίζουμε session
                    del user_sessions[user_id]

                    # Στέλνουμε επιβεβαίωση με κουμπιά Ναι/Όχι για νέα παραγγελία
                    viber.send_messages(user_id, [
                        TextMessage(text=f"✅ Καταχωρήθηκε η παραγγελία σου: {quantity} x {food.capitalize()}.\nΘες να παραγγείλεις κάτι άλλο;", keyboard=confirm_keyboard)
                    ])
                else:
                    viber.send_messages(user_id, [
                        TextMessage(text="Παρακαλώ γράψε αριθμό μεγαλύτερο του 0 για την ποσότητα.")
                    ])
                return Response(status=200)

            elif session.get('waiting_confirm'):
                # Περιμένουμε απάντηση για επιβεβαίωση
                if user_text == "confirm_yes":
                    # Αρχίζουμε νέα παραγγελία
                    user_sessions[user_id] = {}
                    viber.send_messages(user_id, [
                        TextMessage(text="🍽 Τι θα ήθελες να παραγγείλεις;", keyboard=food_keyboard)
                    ])
                elif user_text == "confirm_no":
                    del user_sessions[user_id]
                    viber.send_messages(user_id, [
                        TextMessage(text="Ευχαριστούμε για την παραγγελία! Καλή όρεξη! 👋")
                    ])
                else:
                    viber.send_messages(user_id, [
                        TextMessage(text="Παρακαλώ επίλεξε ✅ Ναι ή ❌ Όχι.", keyboard=confirm_keyboard)
                    ])
                return Response(status=200)

        # Αν ξεκινάει η παραγγελία ή δεν είναι σε session
        if user_text == '/start':
            user_sessions[user_id] = {}
            viber.send_messages(user_id, [
                TextMessage(text="🍽 Τι θα ήθελες να παραγγείλεις;", keyboard=food_keyboard)
            ])
        elif user_text in ['burger', 'pizza', 'salad', 'fries']:
            # Αποθηκεύουμε το φαγητό και ζητάμε ποσότητα
            user_sessions[user_id] = {'food': user_text, 'waiting_quantity': True}
            viber.send_messages(user_id, [
                TextMessage(text=f"Πόσα {user_text} θες; (γράψε αριθμό)")
            ])
        else:
            viber.send_messages(user_id, [
                TextMessage(text="Γράψε `/start` για να ξεκινήσεις νέα παραγγελία.")
            ])

    return Response(status=200)


def set_webhook(viber):
    viber.set_webhook('https://your-bot-url.onrender.com/')  # Βάλε το δικό σου URL

if __name__ == "__main__":
    scheduler = sched.scheduler(time.time, time.sleep)
    scheduler.enter(5, 1, set_webhook, (viber,))
    t = threading.Thread(target=scheduler.run)
    t.start()

    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8443)), debug=True)
