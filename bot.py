import os
import threading
import time
import imaplib
import email
import telebot
from flask import Flask, request
from email.header import decode_header, make_header
from dotenv import load_dotenv

load_dotenv()

# Загружаем переменные окружения
EMAIL = os.getenv("EMAIL")                   # Твой Gmail
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD") # Пароль приложения для Gmail
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")   # Токен Telegram-бота
CHAT_ID = os.getenv("CHAT_ID")                 # ID Telegram-чата или группы
PORT = int(os.getenv("PORT", 5000))            # Порт для Flask (Render задаёт переменную PORT)
IMAP_SERVER = "imap.gmail.com"

# Инициализируем Telegram-бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)



def decode_mime_header(header_value):
    try:
        return str(make_header(decode_header(header_value)))
    except Exception as e:
        # Можно оставить ошибку для отладки, если нужно
        print("DEBUG: Ошибка декодирования заголовка:", e, flush=True)
        return header_value

def check_email_loop():
    """Проверяет входящие письма каждые 30 секунд и пересылает их в Telegram,
    если в теле письма есть слово 'пересечение'."""
    while True:
        try:
            print("DEBUG: Проверяю почту...", flush=True)
            mail = imaplib.IMAP4_SSL(IMAP_SERVER)
            mail.login(EMAIL, EMAIL_PASSWORD)
            mail.select("inbox")
            
            result, data = mail.search(None, "UNSEEN")
            email_ids = data[0].split()
            print(f"DEBUG: Найдено непрочитанных писем: {len(email_ids)}", flush=True)
            
            if email_ids:
                for num in email_ids:
                    result, msg_data = mail.fetch(num, "(RFC822)")
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    # Декодируем заголовок
                    raw_subject = msg["Subject"] if msg["Subject"] else ""
                    subject = decode_mime_header(raw_subject)
                    
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body += part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    else:
                        body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                    
                    print("DEBUG: Обнаружено письмо:", flush=True)
                    print("DEBUG: Тема:", subject, flush=True)
                    print("DEBUG: Тело письма:", body, flush=True)
                    
                    # Фильтрация: обрабатываем письмо, только если в теле есть слово "пересечение"
                    if "пересечение" not in body.lower():
                        print("DEBUG: Письмо пропущено (ключевое слово не найдено)", flush=True)
                        continue
                    
                    message_text = f"{subject}\n\n{body}"
                    bot.send_message(CHAT_ID, message_text)
                    print(f"DEBUG: Отправлено в Telegram: {subject}", flush=True)
            else:
                print("DEBUG: Нет новых писем.", flush=True)
            
            mail.close()
            mail.logout()
        except Exception as e:
            print(f"DEBUG: Ошибка при получении писем: {e}", flush=True)
        
        time.sleep(30)

# Создаем Flask-приложение (необходимо для деплоя на Render)
app = Flask(__name__)

# Эндпоинт для TradingView (если понадобится, можно использовать для вебхуков)
@app.route("/tradingview", methods=["POST"])
def tradingview_alert():
    data = request.get_json()
    print("Получен сигнал от TradingView:", data)
    return {"status": "ok"}, 200

if __name__ == "__main__":
    email_thread = threading.Thread(target=check_email_loop, daemon=True)
    email_thread.start()
    app.run(host="0.0.0.0", port=PORT)

@app.route("/check_email_once", methods=["GET"])
def check_email_once():
    try:
        check_email_loop_once()  # вызов функции проверки почты один раз
        return {"status": "check_email_loop_once выполнена"}, 200
    except Exception as e:
        return {"error": str(e)}, 500

def check_email_loop_once():
    """Выполняет проверку почты один раз для отладки."""
    print("DEBUG: Однократная проверка почты...", flush=True)
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL, EMAIL_PASSWORD)
        mail.select("inbox")
        
        result, data = mail.search(None, "UNSEEN")
        email_ids = data[0].split()
        print(f"DEBUG: Найдено непрочитанных писем: {len(email_ids)}", flush=True)
        
        if email_ids:
            for num in email_ids:
                result, msg_data = mail.fetch(num, "(RFC822)")
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                raw_subject = msg["Subject"] if msg["Subject"] else ""
                subject = decode_mime_header(raw_subject)
                
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body += part.get_payload(decode=True).decode("utf-8", errors="ignore")
                else:
                    body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                
                print("DEBUG: Обнаружено письмо:", flush=True)
                print("DEBUG: Тема:", subject, flush=True)
                print("DEBUG: Тело письма:", body, flush=True)
                
                if "пересечение" not in body.lower():
                    print("DEBUG: Письмо пропущено (ключевое слово не найдено)", flush=True)
                    continue
                
                message_text = f"{subject}\n\n{body}"
                bot.send_message(CHAT_ID, message_text)
                print(f"DEBUG: Отправлено в Telegram: {subject}", flush=True)
        else:
            print("DEBUG: Нет новых писем.", flush=True)
        
        mail.close()
        mail.logout()
    except Exception as e:
        print(f"DEBUG: Ошибка при однократной проверке почты: {e}", flush=True)