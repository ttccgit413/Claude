import os
import requests
from dotenv import load_dotenv

load_dotenv()


def telegram(message: str) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=10)
    resp.raise_for_status()
