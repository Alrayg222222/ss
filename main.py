from flask import Flask, request
import threading
import imaplib
import email
import re
import requests
import os
from datetime import datetime, timedelta

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")

EMAILS = [
    {
        "email": os.getenv("EMAIL1"),
        "password": os.getenv("PASS1"),
        "imap_server": "imap.gmail.com",
    },
    {
        "email": os.getenv("EMAIL2"),
        "password": os.getenv("PASS2"),
        "imap_server": "imap.gmail.com",
    },
    {
        "email": os.getenv("EMAIL3"),
        "password": os.getenv("PASS3"),
        "imap_server": "imap.gmail.com",
    },
]

PHRASES = {
    "noreply@steampowered.com": "It looks like you are trying to log in from a new device",
    "noreply@rockstargames.com": "Enter this code on the identity verification screen:"
}

user_requests = {}
last_message_time = {}

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
            user_requests[chat_id] = {"count": 0, "blocked_until": None, "warned": False}
        if chat_id in last_message_time and (now - last_message_time[chat_id]).total_seconds() < 1:
            return "Spam ignored"
        last_message_time[chat_id] = now

        if user_requests[chat_id]["blocked_until"] and now < user_requests[chat_id]["blocked_until"]:
            send_to_telegram(chat_id, "تم حظرك مؤقتًا لمدة 6 ساعات بسبب كثرة الطلبات. حاول لاحقًا.")
            return "Blocked"

        if text in ["1", "١"]:
            send_to_telegram(chat_id, "مرحبًا بك ، أنا بوت الأكواد لمتجر شارك قيمينق 😀✋🏻\nاختر الخدمة:\n2 للحصول على كود ستيم ريد ديد\n3 للحصول على كود روكو ستار ريد ديد\n8 للحصول على كود لعبة قراند")

        elif text in ["8", "٨"]:
            send_to_telegram(chat_id, "هل الكود للعبة قراند 4؟ اضغط 9")

        elif text in ["2", "٢"]:
            send_to_telegram(chat_id, "هل الكود للعبة ريد ديد 1؟ اضغط 4\nهل الكود للعبة ريد ديد 2؟ اضغط 5")

        elif text in ["3", "٣"]:
            send_to_telegram(chat_id, "هل الكود للعبة ريد ديد 1؟ اضغط 6\nهل الكود للعبة ريد ديد 2؟ اضغط 7")

        elif text in ["4", "٤", "5", "٥", "6", "٦", "7", "٧", "9", "٩"]:
            user_requests[chat_id]["count"] += 1
            if user_requests[chat_id]["count"] > 17 and not user_requests[chat_id]["warned"]:
                send_to_telegram(chat_id, "تنبيه: تبقى لديك ٣ محاولات قبل الحظر المؤقت.")
                user_requests[chat_id]["warned"] = True
            if user_requests[chat_id]["count"] > 20:
                user_requests[chat_id]["blocked_until"] = now + timedelta(hours=6)
                send_to_telegram(chat_id, "تم حظرك مؤقتًا لمدة 6 ساعات بسبب كثرة الطلبات. حاول لاحقًا.")
                return "Blocked"
            mapping = {
                "4": ("noreply@steampowered.com", 0, "ستيم للعبة ريد ديد 1"),
                "٤": ("noreply@steampowered.com", 0, "ستيم للعبة ريد ديد 1"),
              #  "5": ("noreply@steampowered.com", 1, "ستيم للعبة ريد ديد 2"),
               # "٥": ("noreply@steampowered.com", 1, "ستيم للعبة ريد ديد 2"),
                "6": ("noreply@rockstargames.com", 0, "روكو ستار للعبة ريد ديد 1"),
                "٦": ("noreply@rockstargames.com", 0, "روكو ستار للعبة ريد ديد 1"),
              #  "7": ("noreply@rockstargames.com", 1, "روكو ستار للعبة ريد ديد 2"),
              #  "٧": ("noreply@rockstargames.com", 1, "روكو ستار للعبة ريد ديد 2"),
             #   "9": ("noreply@rockstargames.com", 2, "روكو ستار للعبة قراند 4"),
             #   "٩": ("noreply@rockstargames.com", 2, "روكو ستار للعبة قراند 4"),
            }
            source, email_index, desc = mapping[text]
            send_to_telegram(chat_id, f"جارٍ البحث عن كود {desc}...")
            threading.Thread(target=check_latest_code, args=(chat_id, source, email_index)).start()
        else:
            send_to_telegram(chat_id, "الادخال غير صحيح. الرجاء اختيار رقم :\n1 : القائمة الرئيسية\n2 : كود ستيم\n3 : كود روكو ستار")
    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
