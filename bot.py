import asyncio
import os
import requests
import telegram
from flask import Flask
import threading
from dotenv import load_dotenv

# === 환경변수 불러오기 ===
load_dotenv()

API_KEY = os.getenv("API_KEY")
CHAT_ID = os.getenv("CHAT_ID")
ALERT_CHAT_ID = os.getenv("ALERT_CHAT_ID")
LOG_CHAT_ID = os.getenv("LOG_CHAT_ID")

# === 환경변수 디버깅 출력 ===
print("[INIT] API_KEY:", API_KEY)
print("[INIT] CHAT_ID:", CHAT_ID)
print("[INIT] ALERT_CHAT_ID:", repr(ALERT_CHAT_ID))
print("[INIT] LOG_CHAT_ID:", repr(LOG_CHAT_ID))

# === 텔레그램 봇 객체 ===
bot = telegram.Bot(token=API_KEY)

# === Flask 서버 (Render 슬립 방지용) ===
app = Flask(__name__)

@app.route('/')
def index():
    return "CoinGecko Trending Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

# === 이전 트렌드 저장용 ===
last_list = None  # str 비교를 위한 초기값

# === CoinGecko에서 트렌드 가져오기 ===
def get_trending():
    url = "https://api.coingecko.com/api/v3/search/trending"
    print("[DEBUG] CoinGecko 요청 시작")
    res = requests.get(url, timeout=10)
    res.raise_for_status()
    data = res.json()
    trending = data.get("coins", [])
    return [(i+1, coin["item"]["name"], coin["item"]["symbol"]) for i, coin in enumerate(trending)]

# === 포맷팅 ===
def format_trending(trend_list):
    return "\n".join([f"[{rank}] {name} ({symbol})" for rank, name, symbol in trend_list])

# === 트렌드 체크 및 메시지 전송 ===
async def check_and_notify():
    global last_list
    try:
        print("[DEBUG] check_and_notify() 시작")
        print("[DEBUG] CHAT_ID:", repr(CHAT_ID))
        print("[DEBUG] ALERT_CHAT_ID:", repr(ALERT_CHAT_ID))
        print("[DEBUG] LOG_CHAT_ID:", repr(LOG_CHAT_ID))

        current = get_trending()
        current_str = str(current)

        if last_list is None or current_str != last_list:
            print("[INFO] 트렌드 변경 감지")
            last_list = current_str
            msg = format_trending(current)

            print("[SEND] ALERT_CHAT_ID로 전송 시도")
            await bot.send_message(chat_id=int(ALERT_CHAT_ID), text=f"#ALERT\n📈 CoinGecko 트렌드 변경!\n\n{msg}")

            print("[SEND] LOG_CHAT_ID로 전송 시도")
            await bot.send_message(chat_id=int(LOG_CHAT_ID), text=f"(Changed)\n\n{msg}")

            print("[SEND] CHAT_ID로 전송 시도")
            await bot.send_message(chat_id=int(CHAT_ID), text=f"[ALERT COPY]\n\n{msg}")
        else:
            print("[INFO] 트렌드 동일 → 로그 채널로 조용히 전송")
            print("[SEND] LOG_CHAT_ID로 전송 시도")
            await bot.send_message(chat_id=int(LOG_CHAT_ID), text="(No Change) 트렌드 동일. 변화 없음.")

            print("[SEND] CHAT_ID로 전송 시도")
            await bot.send_message(chat_id=int(CHAT_ID), text="(No Change) 개인 알림 백업")

    except Exception as e:
        import traceback
        print("[ERROR] 예외 발생:")
        traceback.print_exc()

# === 메인 루프 ===
async def main_loop():
    while True:
        print("[LOOP] ===== 시작 =====")
        await check_and_notify()
        print("[LOOP] ===== 대기 중 =====")
        await asyncio.sleep(60)

# === 실행 ===
if __name__ == "__main__":
    try:
        threading.Thread(target=run_flask, daemon=True).start()
        print("[MAIN] 봇 시작. 루프 실행")
        asyncio.run(main_loop())
    except Exception as e:
        import traceback
        print("[FATAL ERROR] 메인 루프 예외 발생:")
        traceback.print_exc()
