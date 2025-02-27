import os
import threading
import time
import imaplib
import email
import telebot
from flask import Flask, request

# Загружаем переменные окружения
EMAIL = os.getenv("EMAIL")                   # Твой Gmail
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD") # Пароль приложения для Gmail
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")   # Токен Telegram-бота
CHAT_ID = os.getenv("CHAT_ID")                 # ID Telegram-чата или группы
PORT = int(os.getenv("PORT", 5000))            # Порт для Flask (Render задаёт переменную PORT)
IMAP_SERVER = "imap.gmail.com"

# Инициализируем Telegram-бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

def check_email_loop():
    """Проверяет входящие письма каждые 30 секунд и пересылает их в Telegram,
    если тело письма содержит ключевое слово "пересечение" (без учета регистра)."""
    while True:
        try:
            print("DEBUG: Проверяю почту...")
            mail = imaplib.IMAP4_SSL(IMAP_SERVER)
            mail.login(EMAIL, EMAIL_PASSWORD)
            mail.select("inbox")

            # Получаем список непрочитанных писем
            result, data = mail.search(None, "UNSEEN")
            email_ids = data[0].split()

            print(f"DEBUG: Найдено писем: {len(email_ids)}")

            if email_ids:
                for num in email_ids:
                    result, msg_data = mail.fetch(num, "(RFC822)")
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    subject = msg["Subject"] if msg["Subject"] else ""
                    body = ""

                    # Собираем текст письма
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body += part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    else:
                        body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

                    print("DEBUG: Обнаружено письмо:")
                    print("Тема:", subject)
                    print("Тело письма:", body)

                    # Фильтрация: письмо обрабатывается, только если в теле есть слово "пересечение"
                    if "пересечение" not in body.lower():
                        print("DEBUG: Письмо пропущено (ключевое слово не найдено).")
                        continue

                    # Формируем сообщение: выводим только тему и тело письма
                    message_text = f"{subject}\n\n{body}"
                    bot.send_message(CHAT_ID, message_text)
                    print(f"DEBUG: Отправлено в Telegram: {subject}")

            else:
                print("DEBUG: Нет новых писем.")

            mail.close()
            mail.logout()

        except Exception as e:
            print(f"Ошибка при получении писем: {e}")

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
    # Запускаем фоновый поток для проверки почты
    email_thread = threading.Thread(target=check_email_loop, daemon=True)
    email_thread.start()

    # Запускаем Flask-сервер на указанном порту
    app.run(host="0.0.0.0", port=PORT)