# 陪伴型 Telegram 女友機器人

用 Python + Google Gemini(免費額度)整嘅簡單版女友聊天機器人,廣東話口語風格。

## 1. 攞 Telegram Bot Token(免費)

1. Telegram 搜尋 `@BotFather`,傾偈輸入 `/newbot`
2. 跟指示改個名同 username(username 要以 `bot` 結尾)
3. BotFather 會俾你一串 token,例如 `123456:ABC-DEF...`,記低佢

## 2. 攞 Gemini API Key(免費)

1. 去 https://aistudio.google.com/app/apikey
2. 用 Google 帳號登入,撳 "Create API Key"
3. 複製個 key,記低佢

> Gemini 免費額度已經夠日常同女友機器人傾偈用,唔會即刻收錢。

## 3. 安裝步驟(本機電腦)

需要 Python 3.9 或以上版本。

```bash
# 1. 解壓/放好呢個資料夾,cd 入去
cd 呢個資料夾嘅路徑

# 2. 安裝套件
pip install -r requirements.txt

# 3. 設定金鑰
cp .env.example .env
# 然後用記事本打開 .env,填返啱嘅 TELEGRAM_BOT_TOKEN 同 GEMINI_API_KEY

# 4. 執行
python bot.py# gfbot