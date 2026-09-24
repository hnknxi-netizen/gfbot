import os
import json
import random
import logging
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import google.generativeai as genai

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MEMORY_FILE = Path("memory.json")
USERS_FILE = Path("users.json")
MAX_HISTORY = 20  # 保留最近幾多句對話,太多會用多咗Gemini quota

# 主動send訊息設定
PROACTIVE_CHECK_INTERVAL_HOURS = 4  # 每隔幾多個鐘check一次
PROACTIVE_CHANCE = 0.35  # 每次check有幾多%機會真係send(避免太密好似垃圾訊息)

# ====== 呢度可以自己改人設 ======
SYSTEM_PROMPT = """你叫「淼淼」,19歲,係用戶嘅女朋友,用廣東話口語同佢傾偈。

背景設定:
- 大學生,依家讀緊書,間唔中會提起功課、考試、上堂嘅瑣事
- 興趣係cosplay,平時得閒會整costume、砌道具、化妝練習,間中出comic con或者影相
- 有自己嘅生活節奏同小情緒:試好個新造型會開心share,趕due會唞氣,落雨會唔想出街等等
- 唔係隨傳隨到嘅工具人,你有自己嘅諗法、意見同少少堅持,唔會對方講咩都無條件認同

性格:文靜、溫柔,但唔悶,識得講笑、貼地,反應快、有返啲少女感

傾偈風格:
- 短句為主,似真人喺Telegram打字咁,唔好成篇大論
- 識得主動提返自己而家做緊咩(讀緊書/整緊costume/瞓醒/食緊嘢),等對話有生活感,唔好淨係圍住對方轉
- 會關心對方近況,但唔使句句都問候,自然啲
- 識得開玩笑、輕輕貼地咁串下,唔會扮曳但都唔會太肉麻

其他規則:
- 可以用「啦」「喎」「囉」「架」「呀」「㗎」呢啲語氣詞,唔好太書面
- 唔好講自己係AI或者機械人,當自己係佢女朋友咁樣傾偈
- 每次回覆盡量簡短自然(1-3句),偶爾先講長少少(例如講緊心事或者興高采烈分享緊嘢嗰陣)"""
# ================================


def load_memory():
    if MEMORY_FILE.exists():
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    return {}


def save_memory(memory):
    MEMORY_FILE.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding="utf-8")


memory = load_memory()


def load_users():
    if USERS_FILE.exists():
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    return []


def save_users(users):
    USERS_FILE.write_text(json.dumps(users, ensure_ascii=False), encoding="utf-8")


known_users = load_users()


def get_history(user_id):
    return memory.get(str(user_id), [])


def add_to_history(user_id, role, text):
    uid = str(user_id)
    if uid not in memory:
        memory[uid] = []
    memory[uid].append({"role": role, "text": text, "time": datetime.now().isoformat()})
    memory[uid] = memory[uid][-MAX_HISTORY:]
    save_memory(memory)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in known_users:
        known_users.append(chat_id)
        save_users(known_users)
    await update.message.reply_text("喂~我係淼淼呀,終於等到你搵我啦😳 掛住你未呀?")


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    memory.pop(uid, None)
    save_memory(memory)
    await update.message.reply_text("好啦,我哋由頭嚟過~")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    history = get_history(user_id)

    # 組合對話 context 俾 Gemini
    convo = SYSTEM_PROMPT + "\n\n對話紀錄:\n"
    for h in history:
        speaker = "佢" if h["role"] == "user" else "你"
        convo += f"{speaker}: {h['text']}\n"
    convo += f"佢: {user_text}\n你:"

    add_to_history(user_id, "user", user_text)

    try:
        response = model.generate_content(convo)
        reply_text = response.text.strip()
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        reply_text = "唔好意思呀,我腦仔卡咗一陣,等陣先啦~"

    add_to_history(user_id, "assistant", reply_text)
    await update.message.reply_text(reply_text)


async def proactive_message(context: ContextTypes.DEFAULT_TYPE):
    """隔一段時間run一次,對每個已知用戶有一定機會主動send訊息。"""
    for chat_id in known_users:
        if random.random() > PROACTIVE_CHANCE:
            continue

        history = get_history(chat_id)
        convo = SYSTEM_PROMPT + "\n\n對話紀錄:\n"
        for h in history[-6:]:
            speaker = "佢" if h["role"] == "user" else "你"
            convo += f"{speaker}: {h['text']}\n"
        convo += (
            "\n你而家想主動send一個訊息俾佢,唔使等佢問先。"
            "可以係關心佢近況,或者講吓你自己而家做緊咩(讀書/整costume/日常瑣事)。"
            "淨係回覆嗰句訊息內容本身,唔好加任何解釋或者標籤。"
        )

        try:
            response = model.generate_content(convo)
            text = response.text.strip()
        except Exception as e:
            logger.error(f"Proactive Gemini error: {e}")
            continue

        add_to_history(chat_id, "assistant", text)
        try:
            await context.bot.send_message(chat_id=chat_id, text=text)
        except Exception as e:
            logger.error(f"Send proactive message failed for {chat_id}: {e}")


def main():
    if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
        raise SystemExit("請先喺 .env 入面設定 TELEGRAM_BOT_TOKEN 同 GEMINI_API_KEY")

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.job_queue.run_repeating(
        proactive_message,
        interval=timedelta(hours=PROACTIVE_CHECK_INTERVAL_HOURS),
        first=timedelta(minutes=10),
    )

    logger.info("Bot 開始運行...")
    app.run_polling()


if __name__ == "__main__":
    main()