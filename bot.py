import asyncio
import telegram
import os
import time
import traceback
import requests
from bs4 import BeautifulSoup
from flask import Flask
import threading

# 환경변수 로딩
API_KEY = os.getenv("API_KEY")
CHAT_ID = os.getenv("CHAT_ID")

print("[INIT] API_KEY:", API_KEY)
print("[INIT] CHAT_ID:", CHAT_ID)

bot = telegram.Bot(token=API_KEY)
last_result = None

# Flask (Render 포트 감지용)
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running!"

def run_flask():
    print("[FLASK] Starting Flask server on port 10000")
    app.run(host="0.0.0.0", port=10000)

# 크롤링 함수 (CoinMarketCap Trending)
def get_trending_data():
    print("[CRAWL] get_trending_data() 시작")
    try:
        url = "https://coinmarketcap.com/trending-cryptocurrencies/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        }

        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        rows = soup.select("table tbody tr")
        print("[CRAWL] row 개수:", len(rows))

        coin_list = []
        for row in rows[:10]:  # 최대 상위 10개
            try:
                name = row.select_one("td:nth-child(3) a").text.strip()
                symbol = row.select_one("td:nth-child(3) p").text.strip()
                coin_list.append((name, symbol))
            except Exception as e:
                print("[WARN] 파싱 실패:", e)
                continue

        print(f"[CRAWL] Parsed {len(coin_list)} coins")
        return coin_list

    except Exception as e:
        traceback.print_exc()
        print(f"[ERROR][CRAWL] {e}")
        return []

# 포맷
def format_trending(coin_list):
    return "\n".join([f"[{i+1}] {name} ({symbol})" for i, (name, symbol) in enumerate(coin_list)])

# 알림 함수
async def check_and_notify():
    global last_result
    print("[DEBUG] check_and_notify() 시작")

    try:
        current_list = get_trending_data()
        if not current_list:
            print("[WARN] current_list is empty")
            return

        if last_result is None:
            print("[INFO] 봇 시작됨. 트렌드 저장만 함.")
            last_result = current_list
            return

        if current_list != last_result:
            formatted = format_trending(current_list)
            print("[INFO] 트렌드 변경 감지됨. 메시지 전송 중")
            await bot.send_message(chat_id=CHAT_ID, text=f"📢 코인 트렌드 변경 감지!\n\n{formatted}")
            last_result = current_list
        else:
            print("[INFO] 트렌드 동일. 메시지 생략.")
    except Exception as e:
        traceback.print_exc()
        print(f"[ERROR][NOTIFY] {e}")

# 루프
async def main_loop():
    while True:
        print("[LOOP] ===== 시작 =====")
        await check_and_notify()
        print("[LOOP] ===== 종료 =====")
        await asyncio.sleep(60)

# 실행
if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    print("[MAIN] 봇 시작. 루프 실행")
    asyncio.run(main_loop())
