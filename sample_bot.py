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

# Προσωρινή αποθήκευση στοιχείων χρηστών
user_sessions = {}

# Google Sheets setup
def get_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_path = os.getenv("GOOGLE_CREDS_PATH", "/etc/secrets/viber-bot-writer-15e183a8df85.json")
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    client = gspread.authorize(creds)
    sheet = client.open("Παραγγελίες").sheet1
    return sheet

def save_order_to_sheet(user_id, order, first_name=None, last_name=None, violation_date=None):
    try:
        sheet = get_sheet()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [user_id, first_name, last_name, violation_date, order, now]
        sheet.append_row(row)
        print("✅ Order saved:", row)
    except Exception as e:
        print("❌ Error saving to sheet:", str(e))

# Custom Keyboard
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
        user_id = viber_request.sender.id
        user_text = viber_request.message.text.strip()

        if user_text.lower() == '/start':
            user_sessions[user_id] = {"step": "first_name"}
            viber.send_messages(user_id, [
                TextMessage(text="📝 Ποιο είναι το *όνομά* σου;")
            ])
            return Response(status=200)

        if user_id in user_sessions:
            session = user_sessions[user_id]
            step = session.get("step")

            if step == "first_name":
                session["first_name"] = user_text
                session["step"] = "last_name"
                viber.send_messages(user_id, [
                    TextMessage(text="📝 Ποιο είναι το *επώνυμό* σου;")
                ])

            elif step == "last_name":
                session["last_name"] = user_text
                session["step"] = "violation_date"
                viber.send_messages(user_id, [
                    TextMessage(text="📅 Ποια είναι η *ημερομηνία παράβασης* (π.χ. 2025-07-28);")
                ])

            elif step == "violation_date":
                session["violation_date"] = user_text
                session["step"] = "order"
                viber.send_messages(user_id, [
                    TextMessage(text="🍽 Τι θα ήθελες να παραγγείλεις;", keyboard=food_keyboard)
                ])
            return Response(status=200)

        elif user_text.lower() in ['burger', 'pizza', 'salad', 'fries']:
            if user_id in user_sessions:
                session = user_sessions.pop(user_id)
                save_order_to_sheet(
                    user_id=user_id,
                    order=user_text.capitalize(),
                    first_name=session.get("first_name"),
                    last_name=session.get("last_name"),
                    violation_date=session.get("violation_date")
                )
                viber.send_messages(user_id, [
                    TextMessage(text=f"✅ Η παραγγελία σου για {user_text.capitalize()} καταχωρήθηκε!")
                ])
            else:
                viber.send_messages(user_id, [
                    TextMessage(text="❗ Πρέπει πρώτα να ξεκινήσεις με `/start`.")
                ])
        else:
            viber.send_messages(user_id, [
                TextMessage(text="❓ Δεν κατάλαβα. Γράψε `/start` για να ξεκινήσεις νέα παραγγελία.")
            ])
    return Response(status=200)

# Webhook
def set_webhook(viber):
    viber.set_webhook('https://your-render-url.onrender.com/')  # άλλαξε το URL

if __name__ == "__main__":
    scheduler = sched.scheduler(time.time, time.sleep)
    scheduler.enter(5, 1, set_webhook, (viber,))
    t = threading.Thread(target=scheduler.run)
    t.start()

    context = ('server.crt', 'server.key') if os.path.exists('server.crt') else None
    app.run(host='0.0.0.0', port=8443, debug=True, ssl_context=context)
