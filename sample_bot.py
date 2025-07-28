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

# Προσωρινή μνήμη χρηστών
user_sessions = {}

# Google Sheets setup
def get_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_path = os.getenv("GOOGLE_CREDS_PATH", "/etc/secrets/viber-bot-writer-15e183a8df85.json")
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    client = gspread.authorize(creds)
    return client.open("Παραγγελίες").sheet1

def save_order_to_sheet(user_id, full_name, violation_date, order):
    try:
        sheet = get_sheet()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [user_id, full_name, violation_date, order, now]
        sheet.append_row(row)
        print("✅ Order saved:", row)
    except Exception as e:
        print("❌ Error saving to sheet:", str(e))

# Πληκτρολόγιο επιλογών φαγητού
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
        full_name = viber_request.sender.name
        user_text = viber_request.message.text.strip()

        # Αν στείλει /start
        if user_text.lower() == '/start':
            user_sessions[user_id] = {"step": "violation_date", "full_name": full_name}
            viber.send_messages(user_id, [
                TextMessage(text="📅 Ποια είναι η *ημερομηνία παράβασης*; (π.χ. 2025-07-28)")
            ])
            return Response(status=200)

        # Αν είναι ήδη σε διαδικασία
        if user_id in user_sessions:
            session = user_sessions[user_id]
            step = session.get("step")

            if step == "violation_date":
                session["violation_date"] = user_text
                session["step"] = "order"
                viber.send_messages(user_id, [
                    TextMessage(text="🍽 Τι θα ήθελες να παραγγείλεις;", keyboard=food_keyboard)
                ])
                return Response(status=200)

            elif step == "order" and user_text.lower() in ['burger', 'pizza', 'salad', 'fries']:
                order = user_text.capitalize()
                save_order_to_sheet(
                    user_id=user_id,
                    full_name=session.get("full_name"),
                    violation_date=session.get("violation_date"),
                    order=order
                )
                del user_sessions[user_id]
                viber.send_messages(user_id, [
                    TextMessage(text=f"✅ Η παραγγελία σου για {order} καταχωρήθηκε!")
                ])
                return Response(status=200)

        # Αν στείλει κάτι άκυρο ή είναι εκτός ροής → επανεκκίνηση
        user_sessions[user_id] = {"step": "violation_date", "full_name": full_name}
        viber.send_messages(user_id, [
            TextMessage(text="🔄 Δεν κατάλαβα. Ξεκινάμε από την αρχή.\n\n📅 Ποια είναι η *ημερομηνία παράβασης*; (π.χ. 2025-07-28)")
        ])
        return Response(status=200)

    return Response(status=200)

# Webhook
def set_webhook(viber):
    viber.set_webhook('https://your-render-url.onrender.com')  # Αντικατάστησέ το με το URL σου

if __name__ == "__main__":
    scheduler = sched.scheduler(time.time, time.sleep)
    scheduler.enter(5, 1, set_webhook, (viber,))
    t = threading.Thread(target=scheduler.run)
    t.start()

    context = ('server.crt', 'server.key') if os.path.exists('server.crt') else None
    app.run(host='0.0.0.0', port=8443, debug=True, ssl_context=context)
