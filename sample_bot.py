from flask import Flask, request, Response
from viberbot import Api
from viberbot.api.bot_configuration import BotConfiguration
from viberbot.api.messages.text_message import TextMessage
from viberbot.api.viber_requests import (
    ViberConversationStartedRequest,
    ViberFailedRequest,
    ViberMessageRequest,
    ViberSubscribedRequest,
    ViberUnsubscribedRequest,
)
from viberbot.api.messages.picture_message import PictureMessage
from viberbot.api.messages.video_message import VideoMessage
from viberbot.api.messages.location_message import LocationMessage
from viberbot.api.messages.contact_message import ContactMessage
from viberbot.api.messages.rich_media_message import RichMediaMessage

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

# 🟩 Custom keyboard (απλό μενού)
custom_keyboard = {
    "Type": "keyboard",
    "DefaultHeight": True,
    "Buttons": [
        {"Columns": 3, "Rows": 1, "Text": "📷 Εικόνα", "ActionType": "reply", "ActionBody": "pic"},
        {"Columns": 3, "Rows": 1, "Text": "🎥 Βίντεο", "ActionType": "reply", "ActionBody": "video"},
        {"Columns": 3, "Rows": 1, "Text": "📍 Τοποθεσία", "ActionType": "reply", "ActionBody": "loc"},
        {"Columns": 3, "Rows": 1, "Text": "📇 Επαφή", "ActionType": "reply", "ActionBody": "contact"},
        {"Columns": 3, "Rows": 1, "Text": "🎠 Carousel", "ActionType": "reply", "ActionBody": "carousel"},
    ]
}

# 🟩 Rich media (carousel)
rich_media = {
    "Type": "rich_media",
    "ButtonsGroupColumns": 6,
    "ButtonsGroupRows": 3,
    "BgColor": "#FFFFFF",
    "Buttons": [
        {
            "Columns": 6,
            "Rows": 2,
            "ActionType": "open-url",
            "ActionBody": "https://example.com/item1",
            "Image": "https://via.placeholder.com/600x300.png?text=Item+1"
        },
        {
            "Columns": 6,
            "Rows": 1,
            "Text": "Item 1 - Δες περισσότερα",
            "ActionType": "open-url",
            "ActionBody": "https://example.com/item1",
            "TextSize": "medium",
            "TextVAlign": "middle",
            "TextHAlign": "center"
        }
    ]
}

@app.route('/', methods=['POST'])
def incoming():
    viber_request = viber.parse_request(request.get_data())

    if isinstance(viber_request, ViberMessageRequest):
        user_text = viber_request.message.text.strip().lower()

        if user_text == '/start':
            viber.send_messages(viber_request.sender.id, [
                TextMessage(text="📲 Καλωσήρθες! Διάλεξε τι θέλεις:", keyboard=custom_keyboard)
            ])

        elif user_text == 'pic':
            viber.send_messages(viber_request.sender.id, [
                PictureMessage(
                    text="Δες αυτή την εικόνα:",
                    media="https://via.placeholder.com/600x400.png?text=Test+Image",
                    thumbnail="https://via.placeholder.com/100x100.png?text=Thumb"
                )
            ])

        elif user_text == 'video':
            viber.send_messages(viber_request.sender.id, [
                VideoMessage(
                    media="https://www.w3schools.com/html/mov_bbb.mp4",
                    size=150000,
                    thumbnail="https://via.placeholder.com/150.png?text=Video+Thumb",
                    text="Δοκιμαστικό βίντεο"
                )
            ])

        elif user_text == 'loc':
            viber.send_messages(viber_request.sender.id, [
                LocationMessage(location={"lat": 37.9838, "lon": 23.7275})
            ])

        elif user_text == 'contact':
            viber.send_messages(viber_request.sender.id, [
                ContactMessage(contact={"name": "Γιάννης Παπαδόπουλος", "phone_number": "+302112345678"})
            ])

        elif user_text == 'carousel':
            viber.send_messages(viber_request.sender.id, [
                RichMediaMessage(rich_media=rich_media)
            ])

        else:
            viber.send_messages(viber_request.sender.id, [
                TextMessage(text="📝 Γράψε `/start` ή επίλεξε μία από τις εντολές.")
            ])

    return Response(status=200)

def set_webhook(viber):
	viber.set_webhook('https://mybotwebserver.com:8443/')

if __name__ == "__main__":
	scheduler = sched.scheduler(time.time, time.sleep)
	scheduler.enter(5, 1, set_webhook, (viber,))
	t = threading.Thread(target=scheduler.run)
	t.start()

	context = ('server.crt', 'server.key')
	app.run(host='0.0.0.0', port=8443, debug=True, ssl_context=context)
