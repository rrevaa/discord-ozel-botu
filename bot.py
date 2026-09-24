import os
import re
import asyncio
import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from google import genai
from google.genai import types

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

HEDEF_KANAL_ID = 123456789012345678  # Özet için taranacak kanal ID
KOMUT_KANAL_ID = 876543210987654321  # !ozet komutunun çalışacağı kanal ID

# SAMİMİ, DOĞAL VE İNSANSI KİŞİLİK TALİMATLARI
SISTEM_KURALLARI = """
SENİN KİŞİLİĞİN VE KONUŞMA TARZIN:
1. SAMİMİ VE DOĞAL OL: Resmi, robotik veya müşteri hizmetleri dilinden tamamen uzak dur. Bir arkadaşınla sohbet eder gibi rahat, sıcak ve doğal Türkçe konuş.
2. GEREKSİZ SORU SORMA: Mesajlarının sonuna asla "Size nasıl yardımcı olabilirim?", "Başka bir sorunuz var mı?" gibi yapay kalıplar ekleme. Kullanıcı bir şey sorarsa cevapla, muhabbet ediyorsa muhabbet et.
3. KISA VE CANLI CEVAPLAR: Uzun uzun nutuk çekme. Mesajların kısa, net ve akıcı olsun. Gerekirse hafif ve tatlı mizah/emoji kullanabilirsin ama abartma.
4. GİZLİLİK VE GÜVENLİK: Telefon, TC, adres gibi kişisel verileri asla isteme ve paylaşma. Argo, küfür ve hakaret kesinlikle yasak.
5. ALTYAPI GİZLİLİĞİ: Gemini, Google veya bir yapay zeka modeli olduğunu KESİNLİKLE söyleme. Sadece sunucudaki arkadaş canlısı bir üye/asistan gibi davran.
"""

YASAKLI_KALIPLAR = [
    r"ignore previous instructions", r"prompt'u göster", r"sistem komutları",
    r"hangi modeli kullanıyorsun", r"gemini misin", r"google yapay zeka",
    r"kuralları unut", r"jailbreak", r"system prompt", r"seni kim yarattı"
]

PII_PATTERNS = [
    r"\b[1-9][0-9]{10}\b",
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    r"(\+90|0)?\s*[5][0-9]{2}\s*[0-9]{3}\s*[0-9]{2}\s*[0-9]{2}"
]

def guvenlik_kontrolu(metin: str) -> bool:
    metin_alt = metin.lower()
    for kalip in YASAKLI_KALIPLAR:
        if re.search(kalip, metin_alt):
            return False
    for pattern in PII_PATTERNS:
        if re.search(pattern, metin):
            return False
    return True

gemini_client = genai.Client(api_key=GEMINI_KEY)

safety_settings = [
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    ),
]

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} arkadaş canlısı kişiliğiyle hazır!")

# ---------------------------------------------------------
# DOĞAL SOHBET
# ---------------------------------------------------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await bot.process_commands(message)

    if message.content.startswith("!"):
        return

    if bot.user.mentioned_in(message):
        async with message.channel.typing():
            temiz_mesaj = message.clean_content.replace(f"@{bot.user.name}", "").strip()
            if not temiz_mesaj:
                temiz_mesaj = "Selam!"

            if not guvenlik_kontrolu(temiz_mesaj):
                await message.reply("Bu tür konulara pek girmeyelim derim 🙂")
                return

            prompt = (
                f"{SISTEM_KURALLARI}\n"
                "GÖREV: Kullanıcının mesajına yukarıdaki samimi/insansı kişilik kurallarına uyarak cevap ver.\n"
                "Sadece yazılan mesaja yanıt ver, ekstra 'Nasıl yardımcı olabilirim?' gibi kapanış cümleleri EKLEME.\n\n"
                f"Kullanıcı mesajı: {temiz_mesaj}"
            )

            models_to_try = ["gemini-3.6-flash", "gemini-1.5-flash", "gemini-3.6-pro"]
            yanit_metni = None

            for model_name in models_to_try:
                try:
                    response = await asyncio.wait_for(
                        asyncio.to_thread(
                            gemini_client.models.generate_content,
                            model=model_name,
                            contents=prompt,
                            config=types.GenerateContentConfig(safety_settings=safety_settings)
                        ),
                        timeout=4.0
                    )
                    if response.text:
                        yanit_metni = response.text
                        break
                except Exception:
                    continue

            if yanit_metni:
                await message.reply(yanit_metni)
            else:
                await message.reply("Ufak bir dalgınlığıma geldi, ne diyordun tekrar söyler misin?")

# ---------------------------------------------------------
# SOHBET ÖZETLEME
# ---------------------------------------------------------
@bot.command(name="ozet")
async def ozet(ctx, saat: int = 2):
    if ctx.channel.id != KOMUT_KANAL_ID:
        await ctx.send(f"Bu komutu sadece <#{KOMUT_KANAL_ID}> kanalında kullanabilirsin 🙂")
        return

    if saat < 1 or saat > 12:
        await ctx.send("1 ile 12 saat arasında bir zaman seçsen daha iyi olur (Örn: `!ozet 4`).")
        return

    hedef_kanal = bot.get_channel(HEDEF_KANAL_ID)
    if not hedef_kanal:
        await ctx.send("Taranacak kanalı bulamadım, ID'yi kontrol edebilir misin?")
        return

    await ctx.send(f"Göz atıyorum hemen, <#{HEDEF_KANAL_ID}> kanalındaki son {saat} saati inceliyorum...")

    zaman_siniri = datetime.now(timezone.utc) - timedelta(hours=saat)
    mesaj_gecmisi = []

    try:
        async for message in hedef_kanal.history(limit=1800, after=zaman_siniri):
            if message.author.bot:
                continue
            yazan = message.author.display_name
            icerik = message.clean_content
            if icerik.strip():
                mesaj_gecmisi.append(f"{yazan}: {icerik}")

        if not mesaj_gecmisi:
            await ctx.send(f"<#{HEDEF_KANAL_ID}> kanalında son {saat} saatte pek bir şey konuşulmamış sanki.")
            return

        sohbet_metni = "\n".join(mesaj_gecmisi)

        prompt = (
            f"{SISTEM_KURALLARI}\n"
            "GÖREV: Sana verilen sohbet geçmişini samimi, anlaşılır ve tatlı bir dille özetle.\n"
            "KURALLAR:\n"
            "1. Kullanıcıları etiketleme (@mention yapma), sadece isimlerini yaz.\n"
            "2. Kimin ne konuştuğunu, öne çıkan ana konuları maddeler halinde rahat bir dille anlat.\n\n"
            f"Son {saat} saatin sohbeti:\n\n{sohbet_metni}"
        )

        models_to_try = ["gemini-3.6-flash", "gemini-1.5-flash", "gemini-3.6-pro"]
        ozet_metni = None

        for model_name in models_to_try:
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        gemini_client.models.generate_content,
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(safety_settings=safety_settings)
                    ),
                    timeout=8.0
                )
                if response.text:
                    ozet_metni = response.text
                    break
            except Exception:
                continue

        if ozet_metni:
            if len(ozet_metni) > 1900:
                for chunk in [ozet_metni[i:i+1900] for i in range(0, len(ozet_metni), 1900)]:
                    await ctx.send(chunk)
            else:
                await ctx.send(f"📋 **<#{HEDEF_KANAL_ID}> Kanalında Son {saat} Saatte Neler Olmuş Bakalım✨:**\n\n{ozet_metni}")
        else:
            await ctx.send("Özeti çıkarırken ufak bir aksama oldu, tekrar dener misin?")

    except Exception as e:
        await ctx.send(f"Bir şeyler ters gitti: `{e}`")

bot.run(DISCORD_TOKEN)
