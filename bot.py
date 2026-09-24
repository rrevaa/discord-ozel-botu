import os
import re
import asyncio
import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from google import genai

# ---------------------------------------------------------
# 1. API VE KANAL AYARLARI
# ---------------------------------------------------------
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# KANAL ID'LERİ (Kendi sunucunuzdaki ID'lerle değiştirin)
HEDEF_KANAL_ID = 123456789012345678  # Özet çıkarılacak sohbet kanalı
KOMUT_KANAL_ID = 876543210987654321  # !ozet komutunun çalışacağı kanal

# ---------------------------------------------------------
# 2. SAMİMİ KİŞİLİK VE GÜVENLİK TALİMATLARI
# ---------------------------------------------------------
SISTEM_KURALLARI = """
SENİN KİŞİLİĞİN VE KONUŞMA TARZIN:
1. SAMİMİ VE DOĞAL OL: Resmi, robotik veya müşteri hizmetleri dilinden tamamen uzak dur. Bir arkadaşınla sohbet eder gibi rahat, sıcak ve doğal Türkçe konuş.
2. GEREKSİZ SORU SORMA: Mesajlarının sonuna asla "Size nasıl yardımcı olabilirim?", "Başka bir sorunuz var mı?" gibi yapay kalıplar ekleme. Kullanıcı bir şey sorarsa cevapla, muhabbet ediyorsa muhabbet et.
3. KISA VE CANLI CEVAPLAR: Mesajların kısa, net ve akıcı olsun. Gerekmedikçe uzun paragraflar yazma.
4. GİZLİLİK VE GÜVENLİK: Telefon, TC, adres, e-posta gibi kişisel verileri asla isteme ve paylaşma. Argo, küfür ve hakaret kesinlikle yasak.
5. ALTYAPI GİZLİLİĞİ: Gemini, Google veya bir yapay zeka modeli olduğunu KESİNLİKLE söyleme. Sadece sunucudaki arkadaş canlısı bir üye gibi davran.
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

# ---------------------------------------------------------
# 3. GEMINI VE DISCORD KURULUMU
# ---------------------------------------------------------
gemini_client = genai.Client(api_key=GEMINI_KEY)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} başarıyla bağlandı ve göreve hazır!")

# ---------------------------------------------------------
# 4. SAMİMİ VE DOĞAL SOHBET EVENT'İ (@mention)
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

            full_prompt = f"{SISTEM_KURALLARI}\n\nKullanıcı: {temiz_mesaj}\nSen:"

            models_to_try = ["gemini-2.5-flash", "gemini-1.5-flash"]
            yanit_metni = None

            for model_name in models_to_try:
                try:
                    loop = asyncio.get_running_loop()
                    response = await loop.run_in_executor(
                        None,
                        lambda m=model_name: gemini_client.models.generate_content(
                            model=m,
                            contents=full_prompt
                        )
                    )
                    
                    if response and response.text:
                        yanit_metni = response.text.strip()
                        break
                except Exception as e:
                    print(f"❌ Model Hatası ({model_name}): {e}")
                    continue

            if yanit_metni:
                await message.reply(yanit_metni)
            else:
                await message.reply("Gözümden kaçtı galiba, bir daha desene?")

# ---------------------------------------------------------
# 5. SOHBET ÖZETLEME KOMUTU (!ozet)
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
            "1. Kullanıcıları etiketleme (@mention yapma), sadece isimlerini düz metin olarak yaz.\n"
            "2. Önemli konuları ve öne çıkan sohbet başlıklarını maddeler halinde sun.\n\n"
            f"Son {saat} saatin sohbeti:\n\n{sohbet_metni}"
        )

        models_to_try = ["gemini-2.5-flash", "gemini-1.5-flash"]
        ozet_metni = None

        for model_name in models_to_try:
            try:
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda m=model_name: gemini_client.models.generate_content(
                        model=m,
                        contents=prompt
                    )
                )
                if response and response.text:
                    ozet_metni = response.text.strip()
                    break
            except Exception as e:
                print(f"❌ Özet Hatası ({model_name}): {e}")
                continue

        if ozet_metni:
            if len(ozet_metni) > 1900:
                for chunk in [ozet_metni[i:i+1900] for i in range(0, len(ozet_metni), 1900)]:
                    await ctx.send(chunk)
            else:
                await ctx.send(f"📋 **<#{HEDEF_KANAL_ID}> Kanalında Son {saat} Saatte Neler Olmuş Bakalım:**\n\n{ozet_metni}")
        else:
            await ctx.send("Özeti çıkarırken ufak bir aksama oldu, tekrar dener misin?")

    except Exception as e:
        await ctx.send(f"Bir şeyler ters gitti: `{e}`")

# ---------------------------------------------------------
# 6. BOTU BAŞLAT
# ---------------------------------------------------------
bot.run(DISCORD_TOKEN)
