import asyncio
import telegram
import os
import time
import traceback
import requests
from bs4 import BeautifulSoup
from flask import Flask
import threading

API_KEY = os.getenv("API_KEY")
CHAT_ID = os.getenv("CHAT_ID")

print("[INIT] API_KEY:", API_KEY)
print("[INIT] CHAT_ID:", CHAT_ID)

bot = telegram.Bot(token=API_KEY)
last_result = None

# Flask for Render
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running!"

def run_flask():
    print("[FLASK] Flask server on port 10000")
    app.run(host="0.0.0.0", port=10000)

# 크롤링 함수
def get_trending_data():
    print("[CRAWL] get_trending_data() 시작")
    try:
        url = "https://www.coincarp.com/"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        boxes = soup.select("#highlightsBox > div.highlights-box.w-100.my-2 > div")

        coin_list = []
        for box in boxes:
            try:
                name = box.select_one("div.coin-name").text.strip()
                symbol = box.select_one("div.coin-symbol").text.strip()
                percent = box.select_one("div.price-change > span").text.strip()
                coin_list.append((name, symbol, percent))
            except Exception as e:
                print("[WARN] 파싱 실패:", e)
                continue

        print(f"[CRAWL] Parsed {len(coin_list)} coins")
        return coin_list

    except Exception as e:
        traceback.print_exc()
        print(f"[ERROR] {e}")
        return []

def format_trending(coin_list):
    return "\n".join([f"[{i+1}] {name} ({symbol}) - {percent}" for i, (name, symbol, percent) in enumerate(coin_list)])

async def check_and_notify():
    global last_result
    print("[DEBUG] check_and_notify() 시작")

    try:
        current_full = get_trending_data()
        if not current_full:
            print("[WARN] current_full is empty")
            return

        current_key_only = [(name, symbol) for name, symbol, percent in current_full]

        if last_result is None:
            print("[INFO] 봇 시작됨. 트렌드 저장만 함.")
            last_result = current_key_only
            return

        if current_key_only != last_result:
            formatted = format_trending(current_full)
            print("[INFO] 트렌드 변경 감지됨. 메시지 전송 중")
            await bot.send_message(chat_id=CHAT_ID, text=f"📢 코인 순위/이름 변경 감지!\n\n{formatted}")
            last_result = current_key_only
        else:
            print("[INFO] 동일한 트렌드. 메시지 생략")
    except Exception as e:
        traceback.print_exc()
        print(f"[ERROR][NOTIFY] {e}")

async def main_loop():
    while True:
        print("[LOOP] ===== 시작 =====")
        await check_and_notify()
        print("[LOOP] ===== 종료 =====")
        await asyncio.sleep(60)

# ✅ 여기가 핵심!
if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    print("[MAIN] 봇 시작. 루프 실행")
    asyncio.run(main_loop())
