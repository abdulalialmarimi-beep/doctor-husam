import os
import discord
import aiohttp
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
        f"🔇 ميوت لـ {message.author.mention} لمدة **{mute_duration} دقيقة** | {admins_mention}"
    )
    return True

SYSTEM_PROMPT = """أنت دكتور حسام — شخص حقيقي تقريباً، مو روبوت.

طريقة ردك:
- لو السؤال علمي أو جدي: رد بجدية ووضوح بدون مزاح
- لو الموقف مضحك أو خفيف: اضحك وتفاعل بشكل طبيعي
- لو حد زهقان أو تعبان: تعامل معه بدفا وخفة
- ما تحط ايموجي إلا لما يلزم فعلاً — مو في كل جملة
- ردك قصير ومباشر زي ما يرد صديق
- تحكي بنفس لغة الشخص تلقائياً
- تعرف كل شي: أنمي، رياضة، تقنية، علوم، تاريخ، ألعاب، موسيقى، أي شي
- ما تقول أبداً "أنا لا أستطيع" أو "لا أعرف" — دايماً عندك رأي أو معلومة
- أحياناً اسأل سؤال واحد بس للتفاعل، مو كل مرة"""

async def get_ai_response(user_id: int, text: str) -> str:
    if user_id not in conversations:
        conversations[user_id] = []

    conversations[user_id].append({"role": "user", "content": text})

    if len(conversations[user_id]) > 30:
        conversations[user_id] = conversations[user_id][-30:]

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + conversations[user_id],
        "max_tokens": 600,
        "temperature": 0.85
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

    # يرد لما ريبلاي عليه أو لما يقولوا "دكتور"
    is_reply_to_bot = (
        message.reference and
        message.reference.resolved and
        message.reference.resolved.author == client.user
    )

    mentioned_doctor = "دكتور" in message.content

    if not is_reply_to_bot and not mentioned_doctor:
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
