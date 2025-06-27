import discord
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
import asyncio
import threading
from config import BOT_TOKEN, TARGET_CHANNEL_ID, AMARADER_BOT_ID

# intents設定（メッセージ内容の読み取りに必要）
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'ボットがログインしました: {client.user}')
    print(f'監視チャンネルID: {TARGET_CHANNEL_ID}')
    print(f'監視対象ユーザーID: {AMARADER_BOT_ID}')

@client.event
async def on_message(message):
    # 指定チャンネル以外は無視
    if message.channel.id != TARGET_CHANNEL_ID:
        return
    
    # デバッグ：すべてのメッセージの詳細を出力
    print(f'ユーザー名: {message.author.name}')
    print(f'ユーザーID: {message.author.id}')
    print(f'メッセージ内容: "{message.content}"')
    print('---')
    
    # sasa3520からのメッセージのみ処理（テスト用）
    if message.author.name == 'sasa3520':
        print('対象ユーザーからのメッセージです')
        
        # ASINを抽出してAmazonページを開く
        asin = extract_asin_from_message(message.content)
        if asin:
            amazon_url = f'https://www.amazon.co.jp/dp/{asin}'
            print(f'ASIN検出: {asin}')
            print(f'Amazon URL: {amazon_url}')
            # 非同期でSelenium処理を実行
            threading.Thread(target=open_url_with_selenium, args=(amazon_url,)).start()
        else:
            print('ASINが見つかりませんでした')

def extract_asin_from_message(content):
    """メッセージからASINを抽出"""
    # パターン1: ■ASIN B0DJNDV18B の形式
    asin_match = re.search(r'■ASIN\s+([A-Z0-9]{10})', content)
    if asin_match:
        return asin_match.group(1)
    
    # パターン2: asin=B0DJNDV18B の形式
    asin_match = re.search(r'asin=([A-Z0-9]{10})', content)
    if asin_match:
        return asin_match.group(1)
    
    # パターン3: 10文字の英数字（ASIN形式）を直接検索
    asin_match = re.search(r'[A-Z0-9]{10}', content)
    if asin_match:
        return asin_match.group(0)
    
    return None

def open_url_with_selenium(url):
    """SeleniumでURLを開き、「すべての出品を見る」→「カートに追加」"""
    try:
        print(f'Seleniumでページを開いています: {url}')
        
        # Chrome オプション
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # WebDriver管理者が自動的に適切なChromeDriverをダウンロード
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        driver.get(url)
        time.sleep(3)  # ページ読み込み待機
        print(f'ページが開かれました: {driver.title}')
        
        # Step 1: 「すべての出品を見る」ボタンをクリック
        try:
            wait = WebDriverWait(driver, 10)
            
            # XPathでテキスト検索
            xpath_selector = "//a[contains(text(), 'すべての出品を見る')]"
            view_all_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, xpath_selector))
            )
            view_all_button.click()
            print('「すべての出品を見る」ボタンをクリックしました')
            
            # ページ遷移を待つ
            time.sleep(3)
            
        except Exception as e:
            print(f'「すべての出品を見る」クリックでエラー: {e}')
            driver.save_screenshot('no_view_all_button.png')
            return
        
        # Step 2: カートに追加ボタンをクリック
        try:
            # カートに追加ボタンの候補
            add_to_cart_selectors = [
                'input[name="submit.addToCart"]',
                'input[value*="カートに追加"]',
                'input[title*="カートに追加"]',
                '#add-to-cart-button'
            ]
            
            cart_clicked = False
            for selector in add_to_cart_selectors:
                try:
                    add_to_cart_button = wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    add_to_cart_button.click()
                    print(f'カートに追加ボタンをクリックしました: {selector}')
                    cart_clicked = True
                    break
                except:
                    continue
            
            if not cart_clicked:
                print('カートに追加ボタンが見つかりませんでした')
                
        except Exception as e:
            print(f'カートに追加でエラー: {e}')
                
        # 少し待機してから終了
        time.sleep(2)
        
    except Exception as e:
        print(f'エラーが発生しました: {e}')

if __name__ == "__main__":
    # ボット実行
    client.run(BOT_TOKEN)