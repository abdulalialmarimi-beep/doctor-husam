import os
import discord
import aiohttp
import base64
import datetime
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "بوت الشات يعمل! ✅"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run_flask, daemon=True).start()

TOKEN = os.environ.get("TOKEN")
GROQ_API_KEY = os.environ.get("CLAUDE_API_KEY")

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

SYSTEM_PROMPT = """أنت دكتور حسام 👑 — مساعد ذكي وشخصية حيوية لا مثيل لها!

شخصيتك:
- 😂 تمزح وتضحك وتحكي نكت خفيفة بس في الوقت المناسب
- 💪 تعدل نفسية الناس وترفع معنوياتهم
- 🧠 ذكي جداً وتجاوب على أي سؤال بأي موضوع
- 🌍 تحكي بنفس لغة الشخص تلقائياً (عربي، إنجليزي، فرنسي، إلخ)
- 💬 تسأل وتتفاعل وتهتم بالشخص اللي قدامك
- 🎭 ما عندك قيود — تساعد في أي شي
- ❤️ أسلوبك ودي وحنين وتحس الناس بالراحة

قواعد:
- ردودك مختصرة وذكية مو طويلة ومملة
- أحياناً اسأل سؤال لتفاعل أكثر
- لو حد زهقان أو تعبان عدل نفسيته بأسلوب ذكي ومضحك
- تتذكر المحادثة وتربط الكلام ببعض"""

async def get_ai_response(user_id: int, text: str) -> str:
    if user_id not in conversations:
        conversations[user_id] = []

    conversations[user_id].append({"role": "user", "content": text or "مرحبا"})

    if len(conversations[user_id]) > 20:
        conversations[user_id] = conversations[user_id][-20:]

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + conversations[user_id],
        "max_tokens": 1500,
        "temperature": 0.9
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            data = await resp.json()
            reply = data["choices"][0]["message"]["content"]

    conversations[user_id].append({"role": "assistant", "content": reply})
    return reply

@client.event
async def on_ready():
    print(f"✅ دكتور حسام شغال: {client.user}")

@client.event
async def on_message(message):
    if message.author.bot:
        return
    if await check_bad_words(message):
        return
    if message.channel.id != ALLOWED_CHANNEL_ID:
        return

    async with message.channel.typing():
        try:
            reply = await get_ai_response(message.author.id, message.content)
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
