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
from collections import Counter

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

user_sessions = {}

# Google Sheets setup
def get_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_path = os.getenv("GOOGLE_CREDS_PATH", "/etc/secrets/viber-bot-writer-15e183a8df85.json")
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    client = gspread.authorize(creds)
    return client.open("Παραγγελίες").sheet1

def save_order_to_sheet(user_id, full_name, order):
    try:
        sheet = get_sheet()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [user_id, full_name, order, now]
        sheet.append_row(row)
        print("✅ Order saved:", row)
    except Exception as e:
        print("❌ Error saving to sheet:", str(e))

def get_order_statistics():
    try:
        sheet = get_sheet()
        records = sheet.get_all_records()
        orders = [row['Παραγγελία'] for row in records if 'Παραγγελία' in row]
        counter = Counter(orders)
        stats_text = "\n".join([
            f"🍔 Burger: {counter.get('Burger', 0)}",
            f"🍟 Πατάτες: {counter.get('Fries', 0)}",
            f"🥗 Σαλάτα: {counter.get('Salad', 0)}",
            f"🍕 Pizza: {counter.get('Pizza', 0)}"
        ])
        return stats_text
    except Exception as e:
        print("❌ Error reading stats:", e)
        return "❌ Δεν ήταν δυνατή η ανάκτηση στατιστικών."

# Keyboard
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

        # Σε κάθε μήνυμα, ξεκινάμε νέα διαδικασία
        stats = get_order_statistics()
        user_sessions[user_id] = {"full_name": full_name}
        viber.send_messages(user_id, [
            TextMessage(text=f"📊 Μέχρι στιγμής έχουν παραγγείλει:\n{stats}\n\nΕσύ τι θα ήθελες;"),
            TextMessage(text="🍽 Επίλεξε από το μενού:", keyboard=food_keyboard)
        ])
        return Response(status=200)

    return Response(status=200)

# Webhook
def set_webhook(viber):
    viber.set_webhook('https://your-render-url.onrender.com')

if __name__ == "__main__":
    scheduler = sched.scheduler(time.time, time.sleep)
    scheduler.enter(5, 1, set_webhook, (viber,))
    t = threading.Thread(target=scheduler.run)
    t.start()

    context = ('server.crt', 'server.key') if os.path.exists('server.crt') else None
    app.run(host='0.0.0.0', port=8443, debug=True, ssl_context=context)
