
from flask import Flask, request
import threading
import imaplib
import email
import re
import requests
from datetime import datetime, timedelta

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

PHRASES = {
    "noreply@steampowered.com": "It looks like you are trying to log in from a new device",
    "noreply@rockstargames.com": "Enter this code on the identity verification screen:"
}

user_requests = {}

def send_to_telegram(chat_id, message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": message})

def extract_code(body):
    match = re.search(r'\b[A-Z0-9]{5,}\b', body)
    return match.group(0) if match else None

def check_account(acc, target_source, result):
    try:
        mail = imaplib.IMAP4_SSL(acc["imap_server"])
        mail.login(acc["email"], acc["password"])
        mail.select("inbox")
        result_search, data = mail.search(None, 'ALL')
        if result_search != "OK":
            return
        for num in data[0].split()[::-1]:
            result_fetch, msg_data = mail.fetch(num, "(RFC822)")
            if result_fetch != "OK":
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            sender = msg["from"]
            if target_source in sender:
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode(errors="ignore")
                            break
                else:
                    body = msg.get_payload(decode=True).decode(errors="ignore")
                if PHRASES[target_source] in body:
                    code = extract_code(body)
                    if code:
                        prefix = "الكود هو: "
                        if "rockstargames" in target_source:
                            prefix = "كود روكو ستار هو: "
                        elif "steampowered" in target_source:
                            prefix = "كود ستيم هو: "
                        result[target_source] = f"{prefix}{code}"
                        break
        mail.logout()
    except Exception as e:
        print(f"خطأ في {acc['email']}: {str(e)}")

def check_latest_code(chat_id, source, email_index):
    acc = EMAILS[email_index]
    result = {}
    check_account(acc, source, result)
    if result.get(source):
        send_to_telegram(chat_id, result[source])
    else:
        send_to_telegram(chat_id, "لم يتم العثور على أي كود.")

@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    if data and "message" in data:
        message = data["message"]
        chat_id = str(message["chat"]["id"])
        text = message.get("text", "").strip()
        now = datetime.now()
        if chat_id not in user_requests:
            user_requests[chat_id] = {"count": 0, "blocked_until": None}

        # Check block status
        if user_requests[chat_id]["blocked_until"] and now < user_requests[chat_id]["blocked_until"]:
            send_to_telegram(chat_id, "تم حظرك مؤقتًا لمدة 12 ساعة بسبب كثرة الطلبات. حاول لاحقًا.")
            return "Blocked"

        # Handle main menu
        if text in ["1", "١"]:
            send_to_telegram(chat_id, "اختر الخدمة:\n٢ للحصول على كود ستيم\n٣ للحصول على كود روكو ستار")
        elif text in ["2", "٢"]:
            send_to_telegram(chat_id, "هل الكود للعبة ريد ديد 1؟ اضغط 4\nهل الكود للعبة ريد ديد 2؟ اضغط 5")
        elif text in ["3", "٣"]:
            send_to_telegram(chat_id, "هل الكود للعبة ريد ديد 1؟ اضغط 6\nهل الكود للعبة ريد ديد 2؟ اضغط 7")
        elif text in ["4", "5", "6", "7"]:
            user_requests[chat_id]["count"] += 1
            if user_requests[chat_id]["count"] > 20:
                user_requests[chat_id]["blocked_until"] = now + timedelta(hours=12)
                send_to_telegram(chat_id, "تم حظرك مؤقتًا لمدة 12 ساعة بسبب كثرة الطلبات. حاول لاحقًا.")
                return "Blocked"
            mapping = {
                "4": ("noreply@steampowered.com", 0, "ستيم للعبة ريد ديد 1"),
                "5": ("noreply@steampowered.com", 1, "ستيم للعبة ريد ديد 2"),
                "6": ("noreply@rockstargames.com", 0, "روكو ستار للعبة ريد ديد 1"),
                "7": ("noreply@rockstargames.com", 1, "روكو ستار للعبة ريد ديد 2"),
            }
            source, email_index, desc = mapping[text]
            send_to_telegram(chat_id, f"جارٍ البحث عن كود {desc}...")
            threading.Thread(target=check_latest_code, args=(chat_id, source, email_index)).start()
    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
