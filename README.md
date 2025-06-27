# Discord通知自動化マニュアル

このマニュアルでは、Discordの特定チャンネルでメッセージを監視し、Amazon商品のASINを検出したら自動でブラウザを開いてカートに追加するPythonプログラムの設定方法を説明します。

## システム概要

**重要：ボットは1つ、実行は各自のPCで**

- **Discordに追加するボット**：1つだけ（管理者が作成）
- **プログラムの実行**：各メンバーが自分のPCで実行
- **動作**：アマレーダー通知が来ると、全メンバーのブラウザで同時にAmazonが開く

つまり、20人のメンバーがいても、Discordサーバーに追加するボットは1つだけです。全員が同じボットトークンを使用して、各自のPCでプログラムを実行します。

## 前提条件

- Windows環境
- Python 3.8以上がインストールされていること
- Google Chromeブラウザがインストールされていること
- Discordアカウントを持っていること

## 1. Pythonパッケージのインストール

コマンドプロンプトまたはPowerShellで以下のコマンドを実行：

```bash
pip install discord.py selenium webdriver-manager
```

## 2. Discord Developer Portalでボットを作成（管理者のみ）

**注意：この作業は管理者（1人）のみが行います。他のメンバーは手順4から開始してください。**

### 2.1 アプリケーションの作成

1. ブラウザで [Discord Developer Portal](https://discord.com/developers/applications) にアクセス
2. Discordアカウントでログイン
3. 右上の「**New Application**」ボタンをクリック
4. アプリケーション名を入力（例：「Amazon Monitor Bot」）
5. 「**Create**」をクリック

### 2.2 ボットの作成

1. 左メニューから「**Bot**」をクリック
2. 「**Add Bot**」をクリック
3. 「**Reset Token**」をクリックしてトークンを生成
4. **トークンをコピーして安全な場所に保存**（後で使用）

### 2.3 重要：Privileged Intentsの有効化

1. 同じ「Bot」ページの下部「**Privileged Gateway Intents**」セクションで：
   - ✅ **Presence Intent** にチェックを入れる
   - ✅ **Server Members Intent** にチェックを入れる
   - ✅ **MESSAGE CONTENT INTENT** にチェックを入れる
 ![image](https://github.com/user-attachments/assets/e8f2fb07-0a04-4a40-9156-01e4ee099d0b)

2. 「**Save Changes**」をクリック

### 2.4 ボットをサーバーに招待

1. 左メニューから「**OAuth2**」→「**URL Generator**」をクリック
2. **Scopes**で「**bot**」にチェック
3. **Bot Permissions**で以下をチェック：
   - View Channels
   - Read Message History
   - Send Messages（必要に応じて）
4. 画面下部に生成されたURLをコピー
5. URLをブラウザで開き、監視したいサーバーを選択
6. 「**認証**」をクリック

### 2.5 ボットトークンの共有

**管理者は作成したボットトークンを、使用する全メンバーに安全に共有してください。**
- Discordのプライベートメッセージ
- セキュアなファイル共有サービス
- チーム内の安全な方法

**⚠️ 注意：ボットトークンは機密情報です。外部に漏洩しないよう注意してください。**

## 3. Discord IDの取得（管理者のみ）

**注意：この作業も管理者のみが行い、取得したIDを全メンバーに共有します。**

### 3.1 開発者モードの有効化

1. Discordアプリで設定（歯車アイコン）をクリック
2. 「**詳細設定**」→「**開発者モード**」をONにする

### 3.2 必要なIDの取得

**チャンネルID:**
1. 監視したいチャンネル名を右クリック
2. 「**IDをコピー**」をクリック

**ボットのユーザーID:**
1. 監視対象のボット（アマレーダー通知など）の名前を右クリック
2. 「**IDをコピー**」をクリック

**サーバーID（参考用）:**
1. サーバー名を右クリック
2. 「**IDをコピー**」をクリック

### 3.3 IDの共有

**管理者は取得したチャンネルIDを全メンバーに共有してください。**

## 4. Pythonコードの設定（全メンバー）

**ここからは各メンバーが自分のPCで行う作業です。**

以下のコードをテキストエディタで作成し、`amazon_monitor.py`として保存：

```python
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

# ★★★ここを自分の値に変更してください★★★
BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'          # 管理者から共有されたボットトークン
TARGET_CHANNEL_ID = 123456789012345678     # 管理者から共有されたチャンネルID
TARGET_BOT_NAME = 'アマレーダー通知'        # 監視対象のボット名（通常は変更不要）

# intents設定（メッセージ内容の読み取りに必要）
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'ボットがログインしました: {client.user}')
    print(f'監視チャンネルID: {TARGET_CHANNEL_ID}')
    print(f'監視対象ボット: {TARGET_BOT_NAME}')

@client.event
async def on_message(message):
    # 指定チャンネル以外は無視
    if message.channel.id != TARGET_CHANNEL_ID:
        return
    
    # 指定ボット以外は無視（アマレーダー通知Botのメッセージのみ処理）
    if message.author.name != TARGET_BOT_NAME:
        return
    
    print(f'アマレーダー通知を検出: {message.content}')
    
    # ASINを抽出してAmazonページを開く
    asin = extract_asin_from_message(message.content)
    if asin:
        amazon_url = f'https://www.amazon.co.jp/dp/{asin}'
        print(f'ASIN検出: {asin}')
        print(f'Amazon URL: {amazon_url}')
        # 非同期でSelenium処理を実行
        threading.Thread(target=open_url_with_selenium, args=(amazon_url,)).start()

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
        time.sleep(3)
        print(f'ページが開かれました: {driver.title}')
        
        # Step 1: 「すべての出品を見る」ボタンをクリック
        try:
            wait = WebDriverWait(driver, 10)
            xpath_selector = "//a[contains(text(), 'すべての出品を見る')]"
            view_all_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, xpath_selector))
            )
            view_all_button.click()
            print('「すべての出品を見る」ボタンをクリックしました')
            time.sleep(3)
            
        except Exception as e:
            print(f'「すべての出品を見る」ボタンが見つかりません: {e}')
            return
        
        # Step 2: カートに追加ボタンをクリック
        try:
            add_to_cart_selectors = [
                'input[name="submit.addToCart"]',
                'input[value*="カートに追加"]',
                '#add-to-cart-button'
            ]
            
            for selector in add_to_cart_selectors:
                try:
                    add_to_cart_button = wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    add_to_cart_button.click()
                    print(f'カートに追加ボタンをクリックしました')
                    break
                except:
                    continue
                    
        except Exception as e:
            print(f'カートに追加でエラー: {e}')
        
        time.sleep(2)
        
    except Exception as e:
        print(f'エラーが発生しました: {e}')

# ボット実行
client.run(BOT_TOKEN)
```

## 5. 設定の変更

コード内の以下の2箇所を変更：

1. `BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'`
   - 管理者から共有されたボットトークンに変更

2. `TARGET_CHANNEL_ID = 123456789012345678`
   - 管理者から共有されたチャンネルIDに変更（数字のみ、クォート不要）

**注意：**
- `TARGET_BOT_NAME`は通常変更不要（アマレーダー通知Botの名前が違う場合のみ変更）

## 6. 実行

1. コマンドプロンプトでPythonファイルがある場所に移動
2. 以下のコマンドで実行：
```bash
python amazon_monitor.py
```

3. 「ボットがログインしました」と表示されれば成功

## 7. 動作確認

1. アマレーダー通知Botがチャンネルに価格通知を送信
2. **全メンバーのPC**でプログラムが反応し、それぞれのブラウザでAmazonページが開く
3. 自動で「すべての出品を見る」をクリック
4. 自動でカートに追加をクリック

**重要：**
- 各メンバーは自分のAmazonアカウントでカートに追加される
- 同じ商品が複数人のカートに同時に追加される

## 8. よくある質問

### Q: なぜボットは1つだけで、20人全員が使えるのですか？

A: ボットの役割は「メッセージを読み取るだけ」だからです。
- アマレーダー通知Botが価格情報を投稿
- 監視ボット（1つ）がそのメッセージを検出
- 20台のPCが同じボットトークンで同時にDiscordに接続
- 各PCで独立してブラウザが開く

### Q: 同じボットトークンを複数人で使っても大丈夫ですか？

A: はい、Discord APIの仕様上、同じトークンで複数の場所から接続可能です。

### Q: 他の人がプログラムを停止していても、自分のプログラムは動きますか？

A: はい、各自のプログラムは独立して動作します。

## トラブルシューティング

### エラー: PrivilegedIntentsRequired
- 管理者が手順2.3の「MESSAGE CONTENT INTENT」を有効にしていない
- 管理者にDiscord Developer Portalでの設定確認を依頼

### エラー: Forbidden
- ボットがサーバーに招待されていない
- 管理者に手順2.4の再実行を依頼

### 複数のプログラムが同時に動作している警告
- 同じボットトークンで複数のプログラムが動いているのは正常です
- エラーではありません

### ChromeDriverエラー
- Chromeブラウザを最新版に更新
- 以下のコマンドでパッケージを更新：
```bash
pip install --upgrade selenium webdriver-manager
```

### メッセージが検出されない
- チャンネルIDが正しいか確認
- ボット名が正確に一致しているか確認

## セキュリティ注意事項

- **ボットトークンは機密情報です**
- チーム内でのみ共有し、外部に漏洩させない
- GitHubなどにコードを公開する際はトークンを削除
- 管理者はトークンの定期的な再生成を検討

## 管理者向け：メンバー管理

### ボットトークンの再生成
メンバーの脱退時や漏洩が疑われる場合：
1. Discord Developer Portalで「Reset Token」
2. 新しいトークンを残るメンバーに再配布

### 使用状況の確認
- Discord Developer Portalの「Bot」ページで接続状況を確認可能
- 同時接続数でアクティブなメンバー数を把握

## カスタマイズ

- `TARGET_BOT_NAME`を変更して他のボットを監視可能
- `extract_asin_from_message`関数でメッセージ形式をカスタマイズ可能
- Seleniumの動作を調整して他のアクションを追加可能

## 運用のベストプラクティス

1. **テスト環境での確認**
   - 本番運用前に少数メンバーでテスト実施

2. **定期的なメンテナンス**
   - ChromeDriverの更新
   - Pythonパッケージの更新

3. **トラブル時の対応**
   - 管理者が問題の一次対応を担当
   - 共通の問題は管理者がまとめて解決
