import asyncio
import telegram
import os
import time
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from flask import Flask
import threading

# 환경변수 로딩
API_KEY = os.getenv("API_KEY")
CHAT_ID = os.getenv("CHAT_ID")

print("[INIT] API_KEY:", API_KEY)
print("[INIT] CHAT_ID:", CHAT_ID)

bot = telegram.Bot(token=API_KEY)
last_result = None

# Flask 앱
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running!"

def run_flask():
    print("[FLASK] Starting Flask server on port 10000")
    app.run(host='0.0.0.0', port=10000)

# 크롤링 함수
def get_trending_data():
    print("[CRAWL] Starting get_trending_data()")

    options = FirefoxOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    try:
        driver = webdriver.Firefox(service=FirefoxService(), options=options)
        driver.get("https://www.coincarp.com/")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#highlightsBox"))
        )

        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

        coin_elements = driver.find_elements(By.CSS_SELECTOR, "#highlightsBox > div.highlights-box.w-100.my-2 > div")

        coin_list = []
        for coin in coin_elements:
            try:
                name = coin.find_element(By.CSS_SELECTOR, "div.coin-name").text.strip()
                symbol = coin.find_element(By.CSS_SELECTOR, "div.coin-symbol").text.strip()
                percent = coin.find_element(By.CSS_SELECTOR, "div.price-change > span").text.strip()
                coin_list.append((name, symbol, percent))
            except Exception as inner_e:
                print("[WARN] Failed to parse coin element:", inner_e)
                continue

        driver.quit()
        print(f"[CRAWL] Parsed {len(coin_list)} coins")
        return coin_list

    except Exception as e:
        traceback.print_exc()
        print(f"[ERROR][CRAWL] {e}")
        return []

# 텍스트 포맷
def format_trending(coin_list):
    return "\n".join([f"[{i+1}] {name} ({symbol}) - {percent}" for i, (name, symbol, percent) in enumerate(coin_list)])

# 알림 함수
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
            print("[INFO] 트렌드 변경 감지됨. 텔레그램 전송 시도")
            await bot.send_message(chat_id=CHAT_ID, text=f"📢 코인 순위/이름 변경 감지!\n\n{formatted}")
            last_result = current_key_only
        else:
            print("[INFO] 코인 순위/이름 동일. 메시지 생략.")
    except Exception as e:
        traceback.print_exc()
        print(f"[ERROR][NOTIFY] {e}")

# 메인 루프
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

    print("[MAIN] 봇 시작. 메인 루프 실행")
    asyncio.run(main_loop())
