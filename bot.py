import os
import time
import requests
import telegram
from flask import Flask
import threading
from dotenv import load_dotenv

# === 환경변수 불러오기 ===
load_dotenv()

API_KEY = os.getenv("API_KEY")
CHAT_ID = int(os.getenv("CHAT_ID"))
ALERT_CHAT_ID = int(os.getenv("ALERT_CHAT_ID"))
LOG_CHAT_ID = int(os.getenv("LOG_CHAT_ID"))

print("[INIT] API_KEY:", API_KEY)
print("[INIT] CHAT_ID:", CHAT_ID)
print("[INIT] ALERT_CHAT_ID:", ALERT_CHAT_ID)
print("[INIT] LOG_CHAT_ID:", LOG_CHAT_ID)

bot = telegram.Bot(token=API_KEY)

# === Flask 앱 설정 (슬립 방지용) ===
app = Flask(__name__)

@app.route('/')
def index():
    return "CoinGecko Trending Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

# === 이전 트렌드 저장 ===
last_list = None  # [(rank, name, symbol)]

# === CoinGecko 트렌드 가져오기 ===
def get_trending():
    url = "https://api.coingecko.com/api/v3/search/trending"
    print("[DEBUG] CoinGecko 요청 시작")
    res = requests.get(url, timeout=10)
    res.raise_for_status()
    data = res.json()
    return [(i+1, coin["item"]["name"], coin["item"]["symbol"]) for i, coin in enumerate(data.get("coins", []))]

# === 변경 항목 강조 포맷 함수 ===
def format_trending_with_diff(current, prev):
    lines = []
    for i, (rank, name, symbol) in enumerate(current):
        if prev and i < len(prev) and (name, symbol) != (prev[i][1], prev[i][2]):
            line = f"[{rank}] **{name} ({symbol})**"
        else:
            line = f"[{rank}] {name} ({symbol})"
        lines.append(line)
    return "\n".join(lines)

# === 메시지 전송 함수 ===
def send_message_all(message, is_change=True):
    try:
        if is_change:
            bot.send_message(chat_id=ALERT_CHAT_ID, text=f"#ALERT\n📈 CoinGecko 트렌드 변경!\n\n{message}", parse_mode="Markdown")
            bot.send_message(chat_id=LOG_CHAT_ID, text=f"(Changed)\n\n{message}", parse_mode="Markdown")
            bot.send_message(chat_id=CHAT_ID, text=f"[ALERT COPY]\n\n{message}", parse_mode="Markdown")
        else:
            bot.send_message(chat_id=LOG_CHAT_ID, text="(No Change) 트렌드 동일. 변화 없음.")
            bot.send_message(chat_id=CHAT_ID, text="(No Change) 개인 알림 백업")
    except Exception as e:
        print("[ERROR] 메시지 전송 실패:")
        print(e)

# === 메인 반복 로직 ===
def main_loop():
    global last_list
    while True:
        print("[LOOP] ===== 시작 =====")
        try:
            current = get_trending()
            if last_list is None or current != last_list:
                print("[INFO] 트렌드 변경 감지")
                msg = format_trending_with_diff(current, last_list)
                last_list = current
                send_message_all(msg, is_change=True)
            else:
                print("[INFO] 트렌드 동일 → 조용히 로그만 전송")
                send_message_all("", is_change=False)
        except Exception as e:
            print("[ERROR] 루프 예외 발생:")
            print(e)

        print("[LOOP] ===== 60초 대기 =====")
        time.sleep(60)

# === 시작 ===
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("[MAIN] 봇 시작됨. 루프 실행 중...")
    main_loop()
