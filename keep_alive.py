import os
from threading import Thread
from flask import Flask

app = Flask("")


@app.route("/")
def home():
    return "Noctali Bot est en ligne !"


def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
