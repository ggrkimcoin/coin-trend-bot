import asyncio
import os
import time
import requests
import telegram
from flask import Flask
import threading
from dotenv import load_dotenv

# === 환경변수 로딩 ===
load_dotenv()
API_KEY = os.getenv("API_KEY")
CHAT_ID = os.getenv("CHAT_ID")

print("[INIT] API_KEY:", API_KEY)
print("[INIT] CHAT_ID:", CHAT_ID)

bot = telegram.Bot(token=API_KEY)
last_result = None

# === Flask 앱 설정 (Render 포트 감지용) ===
app = Flask(__name__)

@app.route('/')
def index():
    return "CoinGecko Trending Bot is running!"

def run_flask():
    print("[FLASK] Flask server on port 10000")
    app.run(host='0.0.0.0', port=10000)

# === CoinGecko 트렌딩 API로부터 데이터 가져오기 ===
def get_trending_from_api():
    url = "https://api.coingecko.com/api/v3/search/trending"
    res = requests.get(url, timeout=10)
    res.raise_for_status()
    data = res.json()
    trending = data.get("coins", [])
    return [(i+1, coin["item"]["name"], coin["item"]["symbol"]) for i, coin in enumerate(trending)]

# === 포맷팅 ===
def format_trending(trend_list):
    return "\n".join([f"[{rank}] {name} ({symbol})" for rank, name, symbol in trend_list])

# === 체크 및 메시지 전송 ===
async def check_and_notify():
    global last_result
    print("[DEBUG] check_and_notify() 시작")
    try:
        current_list = get_trending_from_api()
        if not current_list:
            print("[WARN] 트렌딩 데이터 없음")
            return

        if last_result is None:
            print("[INFO] 봇 시작됨. 트렌드 저장만 함.")
            last_result = current_list
            return

        if current_list != last_result:
            formatted = format_trending(current_list)
            print("[INFO] 트렌드 변경 감지. 메시지 전송 중")
            await bot.send_message(chat_id=CHAT_ID, text=f"📈 CoinGecko 트렌드 변경 감지!\n\n{formatted}")
            last_result = current_list
        else:
            print("[INFO] 트렌드 동일. 메시지 생략.")

    except Exception as e:
        print(f"[ERROR] {e}")

# === 메인 루프 ===
async def main_loop():
    while True:
        print("[LOOP] ===== 시작 =====")
        await check_and_notify()
        print("[LOOP] ===== 대기 중 =====")
        await asyncio.sleep(60)

# === 실행 ===
if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    print("[MAIN] 봇 시작. 루프 실행")
    asyncio.run(main_loop())
