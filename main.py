
from flask import Flask, request
import threading
import time
import imaplib
import email
import re
import requests

app = Flask(__name__)

BOT_TOKEN = "7282132914:AAHvc6RDY3jSxu8abCOdQG-Tt8rVzZUK7O0"

EMAILS = [
    {
        "email": "sharkgemingred1@gmail.com",
        "password": "pbhg bwoe xkxr rbld",
        "imap_server": "imap.gmail.com",
    },
    {
        "email": "alraygshahid7@gmail.com",
        "password": "rcmn mmwl jina pcit",
        "imap_server": "imap.gmail.com",
    },
]

TRIGGERS = ["1", "١"]
PHRASES = [
    "Enter this code on the identity verification screen:",
    "It looks like you are trying to log in from a new device. Here is the Steam Guard code you need to access your account:",
    "Your two-factor sign in code"
]
SOURCES = ["noreply@rockstargames.com", "noreply@steampowered.com"]

active_chat_ids = set()

def send_to_telegram(chat_id, message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": message})

def extract_code_from_body(body):
    match = re.search(r'\b[A-Z0-9]{5,}\b', body)
    return match.group(0) if match else None

def check_emails():
    seen_uids = set()
    while True:
        for acc in EMAILS:
            if not acc["email"] or not acc["password"]:
                continue
            try:
                mail = imaplib.IMAP4_SSL(acc["imap_server"])
                mail.login(acc["email"], acc["password"])
                mail.select("inbox")
                result, data = mail.search(None, '(UNSEEN)')
                if result != "OK":
                    continue
                for num in data[0].split()[::-1]:
                    if num in seen_uids:
                        continue
                    result, msg_data = mail.fetch(num, "(RFC822)")
                    if result != "OK":
                        continue
                    msg = email.message_from_bytes(msg_data[0][1])
                    sender = msg["from"]
                    if not any(domain in sender for domain in SOURCES):
                        continue
                    seen_uids.add(num)
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode(errors="ignore")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode(errors="ignore")
                    if any(phrase in body for phrase in PHRASES):
                        code = extract_code_from_body(body)
                        if code:
                            prefix = "الكود هو: "
                            if "rockstargames" in sender:
                                prefix = "كود روكو ستار هو: "
                            elif "steampowered" in sender:
                                prefix = "كود ستيم هو: "
                            for chat_id in active_chat_ids:
                                send_to_telegram(chat_id, f"{prefix}{code}")
                            active_chat_ids.clear()
                            break
                mail.logout()
            except Exception as e:
                print(f"خطأ في {acc['email']}: {str(e)}")
        time.sleep(10)

def start_background_thread():
    thread = threading.Thread(target=check_emails)
    thread.daemon = True
    thread.start()

start_background_thread()

@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    if data and "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        if text in TRIGGERS:
            active_chat_ids.add(chat_id)
            send_to_telegram(chat_id, "تم استلام طلبك، سأبحث عن الكود الآن.")
            return "تم تسجيل طلب الكود"
    return "جاهز للعمل"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
