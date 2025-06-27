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
import threading

# 設定ファイルから設定値を読み込み
try:
    from config import BOT_TOKEN, TARGET_CHANNEL_ID, AMARADER_BOT_ID
except ImportError:
    print("エラー: config.py ファイルが見つかりません。")
    print("config.py ファイルを作成し、以下の設定を記述してください:")
    print("BOT_TOKEN = 'your_bot_token_here'")
    print("TARGET_CHANNEL_ID = your_channel_id")
    print("AMARADER_BOT_ID = your_bot_user_id")
    exit(1)

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
    
    # アマレーダー通知Botからのメッセージのみ処理
    if message.author.id == AMARADER_BOT_ID:
        print(f'アマレーダー通知を検出: {message.content}')
        
        # メッセージから情報を抽出
        message_data = extract_notification_data(message.content)
        if message_data:
            asin = message_data['asin']
            target_price = message_data['current_price']
            amazon_url = f'https://www.amazon.co.jp/dp/{asin}'
            
            print(f'ASIN: {asin}, 目標価格: {target_price}円')
            
            # 非同期でSelenium処理を実行
            threading.Thread(target=lambda: open_url_with_selenium(amazon_url, target_price)).start()
        else:
            print('通知形式が認識できませんでした')

def extract_notification_data(content):
    """通知メッセージから価格とASINを抽出"""
    try:
        # 現在価格を抽出（例：現在：4138 円）
        current_price_match = re.search(r'現在：(\d+)\s*円', content)
        if not current_price_match:
            return None
        current_price = int(current_price_match.group(1))
        
        # ASINを抽出
        asin_match = re.search(r'■ASIN\s+([A-Z0-9]{10})', content)
        if not asin_match:
            return None
        asin = asin_match.group(1)
        
        return {
            'current_price': current_price,
            'asin': asin
        }
        
    except Exception as e:
        print(f'メッセージ解析エラー: {e}')
        return None

def open_url_with_selenium(url, target_price):
    """SeleniumでURLを開き、価格が一致する商品をカートに追加"""
    driver = None
    try:
        print(f'Seleniumでページを開いています: {url}')
        print(f'目標価格: {target_price}円')
        
        # Chrome オプション
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        driver.get(url)

        print(f'ページが開かれました: {driver.title}')
        
        # TODO: 最初にboxが出てきた際に「すべての出品を見る」ボタンは表示されないので、まずはboxの要素を探す。
        # TODO: もしかすると最初から「すべての出品を見る」に移動したほうが早いかもしれない
        # Step 1: 「すべての出品を見る」ボタンをクリック
        try:
            wait = WebDriverWait(driver, 10)
            view_all_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'すべての出品を見る')]"))
            )
            view_all_button.click()
            print('「すべての出品を見る」ボタンをクリックしました')
            time.sleep(1)  # ページ遷移を十分に待つ
            
            # URLが変わらない場合は直接移動
            if '/gp/offer-listing/' not in driver.current_url:
                offer_url = url.replace('/dp/', '/gp/offer-listing/') + '/'
                print(f'直接offer-listingページに移動: {offer_url}')
                driver.get(offer_url)
                time.sleep(1)
            
        except Exception as e:
            print(f'「すべての出品を見る」ボタンエラー: {e}')
            # 直接offer-listingページに移動
            offer_url = url.replace('/dp/', '/gp/offer-listing/') + '/'
            print(f'直接移動: {offer_url}')
            driver.get(offer_url)
            time.sleep(1)
        
        print(f'現在のURL: {driver.current_url}')
        
        # Step 2: 価格が一致する商品を探してカートに追加
        # TODO: 価格のコンディションが新品の場合の判定を追加 <span class="a-size-base a-text-bold">     新品    </span>
        # TODO: ほぼ新品もNG
        
        try:
            # 価格要素をすべて取得
            price_elements = driver.find_elements(By.CSS_SELECTOR, '.a-price-whole')
            print(f'見つかった価格要素: {len(price_elements)}個')
            
            target_found = False
            
            for i, price_elem in enumerate(price_elements):
                try:
                    price_text = price_elem.text.strip()
                    print(f'価格 {i+1}: "{price_text}"')
                    
                    # 価格を数値化（カンマを除去）
                    if price_text and price_text.replace(',', '').isdigit():
                        price_value = int(price_text.replace(',', ''))
                        print(f'価格 {i+1}: {price_value}円 (目標: {target_price}円)')
                        
                        # 価格がぴったり一致する場合
                        if price_value == target_price:
                            print(f'目標価格に一致する商品を発見: {price_value}円')
                            
                            # 価格要素の親要素から出品全体を特定
                            offer_section = price_elem
                            for _ in range(10):  # 最大10回上位要素を探索
                                offer_section = offer_section.find_element(By.XPATH, '..')
                                # カートボタンがこのセクション内にあるかチェック
                                cart_buttons = offer_section.find_elements(By.XPATH, './/input[@name="submit.addToCart" or contains(@value, "カートに追加")]')
                                if cart_buttons:
                                    print(f'カートボタンを発見: {cart_buttons[0].get_attribute("value")}')
                                    
                                    # カートに追加をクリック
                                    driver.execute_script("arguments[0].click();", cart_buttons[0])
                                    print(f'✓ {price_value}円の商品をカートに追加しました')
                                    target_found = True
                                    break
                            
                            if target_found:
                                break
                        else:
                            print(f'価格不一致: {price_value}円 ≠ {target_price}円')
                
                except Exception as e:
                    print(f'価格 {i+1} の処理でエラー: {e}')
                    continue
            
            if not target_found:
                print(f'✗ 目標価格 {target_price}円の商品が見つかりませんでした')
                # デバッグ用：見つかった価格をすべて表示
                all_prices = [elem.text.strip() for elem in price_elements if elem.text.strip()]
                print(f'見つかった価格: {all_prices}')
                
        except Exception as e:
            print(f'価格検索でエラー: {e}')
                
        time.sleep(2)
        
    except Exception as e:
        print(f'全体エラー: {e}')

    finally:
        if driver:
            driver.quit()

# ボット実行
client.run(BOT_TOKEN)