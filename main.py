import os
import discord
import aiohttp
import base64
import datetime
from flask import Flask
from threading import Thread

# ─── سيرفر Flask لإبقاء البوت حياً ───────────────────────────────────────────

app = Flask('')

@app.route('/')
def home():
    return "بوت الشات يعمل! ✅"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run_flask, daemon=True).start()

# ─── إعدادات البوت ────────────────────────────────────────────────────────────

TOKEN = os.environ.get("TOKEN")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")

ALLOWED_CHANNEL_ID = 1513329157935988746 # غيّر هذا لـ ID قناتك

# الأدمن اللي يتمنشنون عند السب
ADMIN_IDS = [1407727139251290223, 776860475102330940]

intents = discord.Intents.all()
client = discord.Client(intents=intents)

# ─── ذاكرة المحادثات ──────────────────────────────────────────────────────────

conversations = {}

# ─── قائمة السباب ─────────────────────────────────────────────────────────────

BAD_WORDS_HEAVY = ["كس", "طيز", "زب", "لعن", "ابن الكلب"]  # 20 دقيقة
BAD_WORDS_LIGHT = ["حمار", "غبي", "احمق", "تفو"]           # 10 دقائق

async def check_bad_words(message: discord.Message) -> bool:
    content = message.content.lower()
    mute_duration = 0

    for word in BAD_WORDS_HEAVY:
        if word in content:
            mute_duration = 20
            break

    if not mute_duration:
        for word in BAD_WORDS_LIGHT:
            if word in content:
                mute_duration = 10
                break

    if not mute_duration:
        return False

    # ميوت العضو
    try:
        until = discord.utils.utcnow() + datetime.timedelta(minutes=mute_duration)
        await message.author.timeout(until, reason="السب والشتيمة")
        await message.delete()
    except:
        pass

    # منشن الأدمن
    admins_mention = " ".join([f"<@{aid}>" for aid in ADMIN_IDS])
    await message.channel.send(
        f"🔇 تم إعطاء ميوت لـ {message.author.mention} لمدة **{mute_duration} دقيقة** بسبب السب\n"
        f"📢 {admins_mention}"
    )
    return True

# ─── System Prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """أنت مساعد ذكي متطور تم تطويرك من قبل الملك حسام 👑
- ترد بنفس لغة المستخدم تلقائياً
- ردودك سريعة ومختصرة وذكية
- تفهم الصور وتحللها بدقة
- أسلوبك ودي ومرن
- تساعد في أي موضوع بدون قيود"""

# ─── دالة تحميل الصورة ────────────────────────────────────────────────────────

async def download_image(url: str) -> tuple:
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            data = await resp.read()
            content_type = resp.content_type or "image/jpeg"
            return base64.b64encode(data).decode("utf-8"), content_type

# ─── دالة الرد بالذكاء الاصطناعي ─────────────────────────────────────────────

async def get_ai_response(user_id: int, text: str, image_url: str = None) -> str:
    if user_id not in conversations:
        conversations[user_id] = []

    if image_url:
        try:
            img_data, img_type = await download_image(image_url)
            content = [
                {"type": "image", "source": {"type": "base64", "media_type": img_type, "data": img_data}},
                {"type": "text", "text": text or "وش في الصورة؟"}
            ]
        except:
            content = text or "وش في الصورة؟"
    else:
        content = text

    conversations[user_id].append({"role": "user", "content": content})

    if len(conversations[user_id]) > 20:
        conversations[user_id] = conversations[user_id][-20:]

    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    body = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1500,
        "system": SYSTEM_PROMPT,
        "messages": conversations[user_id]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=body,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            data = await resp.json()
            reply = data["content"][0]["text"]

    conversations[user_id].append({"role": "assistant", "content": reply})
    return reply

# ─── أحداث البوت ──────────────────────────────────────────────────────────────

@client.event
async def on_ready():
    print(f"✅ بوت الشات شغال: {client.user}")

@client.event
async def on_message(message):
    if message.author.bot:
        return

    # فحص السب في كل القنوات
    if await check_bad_words(message):
        return

    if message.channel.id != ALLOWED_CHANNEL_ID:
        return

    image_url = None
    if message.attachments:
        for att in message.attachments:
            if any(att.filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                image_url = att.url
                break

    async with message.channel.typing():
        try:
            reply = await get_ai_response(message.author.id, message.content, image_url)
            if len(reply) > 2000:
                for i in range(0, len(reply), 2000):
                    await message.reply(reply[i:i+2000])
            else:
                await message.reply(reply)
        except aiohttp.ServerTimeoutError:
            await message.reply("⏳ تأخر الرد، جرب مرة ثانية.")
        except Exception as e:
            print(f"[خطأ] {e}")
            await message.reply("❌ صار خطأ، جرب مرة ثانية.")

# ─── تشغيل البوت ──────────────────────────────────────────────────────────────

if TOKEN:
    client.run(TOKEN)
else:
    print("❌ TOKEN غير موجود!")
