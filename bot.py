import asyncio
import telegram
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from flask import Flask
import threading

# 환경변수 로딩
API_KEY = os.getenv("API_KEY")
CHAT_ID = os.getenv("CHAT_ID")

print("API_KEY:", API_KEY)
print("CHAT_ID:", CHAT_ID)

bot = telegram.Bot(token=API_KEY)
last_result = None

# Flask 앱 설정 (Render가 포트 감지할 수 있도록)
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

# 크롤링 함수
def get_trending_data():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--log-level=3')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
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
        except:
            continue

    driver.quit()
    return coin_list

# 텍스트 포맷
def format_trending(coin_list):
    return "\n".join([f"[{i+1}] {name} ({symbol}) - {percent}" for i, (name, symbol, percent) in enumerate(coin_list)])

# 알림 함수
async def check_and_notify():
    global last_result
    try:
        current_full = get_trending_data()
        current_key_only = [(name, symbol) for name, symbol, percent in current_full]

        if last_result is None:
            print("[INFO] 봇 시작됨. 트렌드 저장만 함.")
            last_result = current_key_only
            return

        if current_key_only != last_result:
            formatted = format_trending(current_full)
            await bot.send_message(chat_id=CHAT_ID, text=f"📢 코인 순위/이름 변경 감지!\n\n{formatted}")
            last_result = current_key_only
        else:
            print("[INFO] 코인 순위/이름 동일. 메시지 생략.")
    except Exception as e:
        print(f"[ERROR] {e}")

# 메인 루프
async def main_loop():
    while True:
        await check_and_notify()
        await asyncio.sleep(60)

# 실행
if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    asyncio.run(main_loop())
