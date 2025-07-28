from flask import Flask, request, Response
from viberbot import Api
from viberbot.api.bot_configuration import BotConfiguration
from viberbot.api.messages.text_message import TextMessage
from viberbot.api.viber_requests import (
    ViberMessageRequest,
    ViberConversationStartedRequest,
    ViberSubscribedRequest
)
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from collections import Counter

app = Flask(__name__)

# === Viber config ===
viber = Api(BotConfiguration(
    name='PythonSampleBot',
    avatar='http://viber.com/avatar.jpg',
    auth_token='ΤΟ_ΔΙΚΟ_ΣΟΥ_AUTH_TOKEN'
))

# === Google Sheets config ===
def get_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open("Παραγγελίες")
    sheet = spreadsheet.sheet1
    return sheet

# === Βοηθητικό: αποθήκευση παραγγελίας ===
def save_order(user_id, name, order):
    sheet = get_sheet()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [user_id, name, order, timestamp]
    sheet.append_row(row)
    print(f"✅ Order saved: {row}")

# === Βοηθητικό: στατιστικά ===
def get_order_statistics():
    try:
        sheet = get_sheet()
        records = sheet.get_all_records(expected_headers=["User ID", "Ονοματεπώνυμο", "Παραγγελία", "Timestamp"])
        orders = [row["Παραγγελία"] for row in records]
        counter = Counter(orders)
        return (
            f"📊 Μέχρι στιγμής έχουν παραγγείλει:\n"
            f"🍔 Burger: {counter.get('Burger', 0)}\n"
            f"🍕 Pizza: {counter.get('Pizza', 0)}\n"
            f"🥗 Σαλάτα: {counter.get('Salad', 0)}\n"
            f"🍟 Πατάτες: {counter.get('Fries', 0)}"
        )
    except Exception as e:
        print(f"❌ Error reading stats: {e}")
        return "❌ Δεν ήταν δυνατή η ανάκτηση στατιστικών."

# === Πληκτρολόγιο ===
def get_keyboard():
    return {
        "Type": "keyboard",
        "DefaultHeight": True,
        "Buttons": [
            {"Columns": 3, "Rows": 1, "Text": "🍔 Burger", "ActionType": "reply", "ActionBody": "burger"},
            {"Columns": 3, "Rows": 1, "Text": "🍕 Pizza", "ActionType": "reply", "ActionBody": "pizza"},
            {"Columns": 3, "Rows": 1, "Text": "🥗 Σαλάτα", "ActionType": "reply", "ActionBody": "salad"},
            {"Columns": 3, "Rows": 1, "Text": "🍟 Πατάτες", "ActionType": "reply", "ActionBody": "fries"},
        ]
    }

# === Κύριο endpoint ===
@app.route("/", methods=["POST"])
def incoming():
    viber_request = viber.parse_request(request.get_data())

    # ✅ Πρώτη φορά: Conversation Started
    if isinstance(viber_request, ViberConversationStartedRequest):
        viber.send_messages(
            viber_request.user.id,
            [
                TextMessage(text="👋 Καλώς ήρθες!\nΠατήστε το κουμπί *Έναρξη* για να ξεκινήσουμε ✅")
            ]
        )
        return Response(status=200)

    # ✅ Μήνυμα από χρήστη
    if isinstance(viber_request, ViberMessageRequest):
        message_text = viber_request.message.text.lower()
        user = viber_request.sender
        user_id = user.id
        full_name = user.name.strip()

        if message_text in ["burger", "pizza", "salad", "fries"]:
            order = message_text.capitalize()
            save_order(user_id, full_name, order)
            # Στέλνουμε μήνυμα επιβεβαίωσης με το όνομα του χρήστη
            viber.send_messages(user_id, [
                TextMessage(
                    text=f"✅ {full_name}, η παραγγελία σου για {order} καταχωρήθηκε! Ευχαριστούμε 🙌"
                )
            ])
        else:
            # ✅ Στατιστικά + πληκτρολόγιο σε κάθε άλλο input
            stats = get_order_statistics()
            viber.send_messages(user_id, [
                TextMessage(text=f"{stats}\n\nΕσύ τι θα ήθελες;"),
                TextMessage(text="🍽 Επίλεξε από το μενού:", keyboard=get_keyboard())
            ])

    return Response(status=200)
