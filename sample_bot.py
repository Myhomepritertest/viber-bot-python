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
            viber.send_messages(viber_request.sender.id, [
                TextMessage(text="🍔 Επιλέχθηκε Burger. Η παραγγελία σου καταχωρήθηκε!")
            ])

        elif user_text == 'pizza':
            viber.send_messages(viber_request.sender.id, [
                TextMessage(text="🍕 Επιλέχθηκε Pizza. Η παραγγελία σου καταχωρήθηκε!")
            ])

        elif user_text == 'salad':
            viber.send_messages(viber_request.sender.id, [
                TextMessage(text="🥗 Επιλέχθηκε Σαλάτα. Η παραγγελία σου καταχωρήθηκε!")
            ])

        elif user_text == 'fries':
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
	viber.set_webhook('https://your-bot-url.onrender.com/')  # άλλαξε το URL με το δικό σου!

if __name__ == "__main__":
	scheduler = sched.scheduler(time.time, time.sleep)
	scheduler.enter(5, 1, set_webhook, (viber,))
	t = threading.Thread(target=scheduler.run)
	t.start()

	# Για local με SSL (χρήσιμο σε dev)
	context = ('server.crt', 'server.key')  # αν έχεις πιστοποιητικό
	app.run(host='0.0.0.0', port=8443, debug=True, ssl_context=context)
