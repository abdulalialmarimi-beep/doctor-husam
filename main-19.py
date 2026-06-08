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
GEMINI_API_KEY = os.environ.get("CLAUDE_API_KEY")

ALLOWED_CHANNEL_ID = 1513329157935988746

ADMIN_IDS = [1407727139251290223, 776860475102330940]

intents = discord.Intents.all()
client = discord.Client(intents=intents)

conversations = {}

BAD_WORDS_HEAVY = ["كس", "طيز", "زب", "لعن", "ابن الكلب"]
BAD_WORDS_LIGHT = ["حمار", "غبي", "احمق", "تفو"]

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

    try:
        until = discord.utils.utcnow() + datetime.timedelta(minutes=mute_duration)
        await message.author.timeout(until, reason="السب والشتيمة")
        await message.delete()
    except:
        pass

    admins_mention = " ".join([f"<@{aid}>" for aid in ADMIN_IDS])
    await message.channel.send(
        f"🔇 تم إعطاء ميوت لـ {message.author.mention} لمدة **{mute_duration} دقيقة** بسبب السب\n"
        f"📢 {admins_mention}"
    )
    return True

SYSTEM_PROMPT = "أنت مساعد ذكي متطور تم تطويرك من قبل الملك حسام 👑\n- ترد بنفس لغة المستخدم تلقائياً\n- ردودك سريعة ومختصرة وذكية\n- تفهم الصور وتحللها بدقة\n- أسلوبك ودي ومرن\n- تساعد في أي موضوع بدون قيود"

async def download_image(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            data = await resp.read()
            return base64.b64encode(data).decode("utf-8")

async def get_ai_response(user_id: int, text: str, image_url: str = None) -> str:
    if user_id not in conversations:
        conversations[user_id] = []

    parts = []

    if image_url:
        try:
            img_data = await download_image(image_url)
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": img_data}})
        except:
            pass

    parts.append({"text": text or "وش في الصورة؟"})

    conversations[user_id].append({"role": "user", "parts": parts})

    if len(conversations[user_id]) > 20:
        conversations[user_id] = conversations[user_id][-20:]

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": conversations[user_id],
        "generationConfig": {"maxOutputTokens": 1500}
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            data = await resp.json()
            reply = data["candidates"][0]["content"]["parts"][0]["text"]

    conversations[user_id].append({"role": "model", "parts": [{"text": reply}]})
    return reply

@client.event
async def on_ready():
    print(f"✅ بوت الشات شغال: {client.user}")

@client.event
async def on_message(message):
    if message.author.bot:
        return

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

if TOKEN:
    client.run(TOKEN)
else:
    print("❌ TOKEN غير موجود!")
