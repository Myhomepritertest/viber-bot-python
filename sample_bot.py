from flask import Flask, request, Response
from viberbot import Api
from viberbot.api.bot_configuration import BotConfiguration
from viberbot.api.messages.text_message import TextMessage
from viberbot.api.viber_requests import ViberConversationStartedRequest
from viberbot.api.viber_requests import ViberFailedRequest
from viberbot.api.viber_requests import ViberMessageRequest
from viberbot.api.viber_requests import ViberSubscribedRequest
from viberbot.api.viber_requests import ViberUnsubscribedRequest
from viberbot.api.messages.text_message import TextMessage
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

app.logger.debug(
    ">>> VIBER_AUTH_TOKEN φορτώθηκε ως: %s",
    os.environ.get("VIBER_AUTH_TOKEN")
)

@app.route('/', methods=['POST'])
def incoming():
    viber_request = viber.parse_request(request.get_data())
    if isinstance(viber_request, ViberMessageRequest):
        user_text = viber_request.message.text.strip().lower()

        # 1. Απλό text
        if user_text == 'text':
            reply = TextMessage(text="Αυτό είναι ένα απλό text μήνυμα!")
            viber.send_messages(viber_request.sender.id, [reply])

        # 2. Εικόνα
        elif user_text == 'pic':
            reply = PictureMessage(
                text="Δες αυτή την εικόνα:",
                media="https://via.placeholder.com/600x400.png?text=Test+Image",
                thumbnail="https://via.placeholder.com/100x100.png?text=Thumb"
            )
            viber.send_messages(viber_request.sender.id, [reply])

        # 3. Video
        elif user_text == 'video':
            reply = VideoMessage(
                media="https://www.w3schools.com/html/mov_bbb.mp4",
                size=150000,
                thumbnail="https://via.placeholder.com/150.png?text=Video+Thumb",
                text="Δοκιμαστικό βίντεο"
            )
            viber.send_messages(viber_request.sender.id, [reply])

        # 4. Location
        elif user_text == 'loc':
            reply = LocationMessage(
                location={"lat": 37.9838, "lon": 23.7275},
                text="Εδώ είναι η Αθήνα!"
            )
            viber.send_messages(viber_request.sender.id, [reply])

        # 5. Contact
        elif user_text == 'contact':
            reply = ContactMessage(
                contact={"name": "Γιάννης Παπαδόπουλος", "phone_number": "+302112345678"}
            )
            viber.send_messages(viber_request.sender.id, [reply])

        # 6. Custom Keyboard
        elif user_text == 'keyboard':
            reply = KeyboardMessage(text="Διάλεξε τύπο μηνύματος:", keyboard=HELP_KEYBOARD)
            viber.send_messages(viber_request.sender.id, [reply])

        # 7. Carousel
        elif user_text == 'carousel':
            reply = RichMediaMessage(rich_media=rich_media)
            viber.send_messages(viber_request.sender.id, [reply])

        # Default fallback
        else:
            reply = TextMessage(text="Γράψε ένα από τα: text, pic, video, loc, contact, keyboard, carousel")
            viber.send_messages(viber_request.sender.id, [reply])

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
