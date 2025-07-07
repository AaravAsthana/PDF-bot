from flask import Flask
from pywa import WhatsApp
from configuration import *
from handlers import register

app = Flask(__name__)
wa = WhatsApp(
    phone_id=PHONE_ID,
    token=ACCESS_TOKEN,
    server=app,
    verify_token=VERIFY_TOKEN,
    app_secret=APP_SECRET
)

register(wa)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)