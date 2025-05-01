
from flask import Flask, request
import threading
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
PHRASES = {
    "noreply@steampowered.com": "It looks like you are trying to log in from a new device",
    "noreply@rockstargames.com": "Enter this code on the identity verification screen:"
}

def send_to_telegram(chat_id, message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": message})

def extract_code(body):
    match = re.search(r'\b[A-Z0-9]{5,}\b', body)
    return match.group(0) if match else None

def check_account(acc, results):
    try:
        mail = imaplib.IMAP4_SSL(acc["imap_server"])
        mail.login(acc["email"], acc["password"])
        mail.select("inbox")
        result, data = mail.search(None, 'ALL')
        if result != "OK":
            return
        for num in data[0].split()[::-1]:
            result, msg_data = mail.fetch(num, "(RFC822)")
            if result != "OK":
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            sender = msg["from"]
            for source, phrase in PHRASES.items():
                if source in sender and source not in results:
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode(errors="ignore")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode(errors="ignore")
                    if phrase in body:
                        code = extract_code(body)
                        if code:
                            prefix = "الكود هو: "
                            if "rockstargames" in source:
                                prefix = "كود روكو ستار هو: "
                            elif "steampowered" in source:
                                prefix = "كود ستيم هو: "
                            results[source] = f"{prefix}{code}"
            if len(results) == len(PHRASES):
                break
        mail.logout()
    except Exception as e:
        print(f"خطأ في {acc['email']}: {str(e)}")

def check_latest_codes(chat_id):
    threads = []
    results = {}
    for acc in EMAILS:
        t = threading.Thread(target=check_account, args=(acc, results))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    if results:
        for msg in results.values():
            send_to_telegram(chat_id, msg)
    else:
        send_to_telegram(chat_id, "لم يتم العثور على أي أكواد حالياً.")

@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    if data and "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        if text in TRIGGERS:
            send_to_telegram(chat_id, "جارٍ البحث عن أحدث الأكواد...")
            threading.Thread(target=check_latest_codes, args=(chat_id,)).start()
            return "بدأ البحث"
    return "جاهز للعمل"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
