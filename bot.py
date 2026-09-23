import os
import asyncio
import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from google import genai

# 1. GitHub Secrets üzerinden API anahtarlarını al
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Gemini istemcisini başlat
gemini_client = genai.Client(api_key=GEMINI_KEY)

# Discord Bot izinlerini ayarla
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    try:
        # 1. Discord'daki global tüm slash komutları temizle
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()
        print("✅ Tüm Slash Komutları Discord'dan silindi!")
    except Exception as e:
        print(f"Silme hatası: {e}")
    print(f"✅ {bot.user} başarıyla bağlandı ve aktif!")

@bot.command(name="ozet")
async def ozet(ctx, saat: int = 2):
    if saat < 1 or saat > 5:
        await ctx.send("Lütfen 1 ile 5 arasında bir saat değeri girin (Örn: `!ozet 2`).")
        return

    await ctx.send(f"⏳ Son {saat} saat içerisindeki sohbet heemmmmeeen taranıyor, sonuç birazcık gecikebilir ✨...")

    zaman_siniri = datetime.now(timezone.utc) - timedelta(hours=saat)
    mesaj_gecmisi = []

    try:
        # Son mesajları çek
        async for message in ctx.channel.history(limit=500, after=zaman_siniri):
            if message.author.bot:
                continue
            yazan = message.author.display_name
            icerik = message.clean_content
            if icerik.strip():
                mesaj_gecmisi.append(f"{yazan}: {icerik}")

        if not mesaj_gecmisi:
            await ctx.send(f"Son {saat} saat içinde özetlenecek herhangi bir kullanıcı mesajı bulunamadı.")
            return

        sohbet_metni = "\n".join(mesaj_gecmisi)

        prompt = (
            "Sen bir Discord topluluk asistanısın. Sana verilen sohbet geçmişinin "
            "geniş, anlaşılır ve derli toplu bir özetini çıkar.\n"
            "ÖNEMLİ KURALLAR:\n"
            "1. Kesinlikle kullanıcıları etiketleme (@mention yapma), sadece isimlerini düz metin olarak an.\n"
            "2. Önemli konuları, alınan kararları ve öne çıkan sohbet başlıklarını maddeler halinde sun.\n\n"
            f"İşte son {saat} saatin sohbet geçmişi:\n\n{sohbet_metni}"
        )

        # 503 ve sunucu yoğunluğu hatalarına karşı yedekli model listesi
        models_to_try = ["gemini-3.6-flash", "gemini-2.5-flash"]
        ozet_metni = None
        son_hata = None

        # Modelleri sırayla dene ve 503 hatasında bekle
        for model_name in models_to_try:
            for deneme in range(2): # Her model için 2 defa dene
                try:
                    response = gemini_client.models.generate_content(
                        model=model_name,
                        contents=prompt
                    )
                    ozet_metni = response.text
                    break
                except Exception as e:
                    son_hata = e
                    if "503" in str(e):
                        await asyncio.sleep(2) # 503 aldıysa 2 saniye bekle
                        continue
                    else:
                        break
            if ozet_metni:
                break

        if ozet_metni:
            if len(ozet_metni) > 1900:
                for chunk in [ozet_metni[i:i+1900] for i in range(0, len(ozet_metni), 1900)]:
                    await ctx.send(chunk)
            else:
                await ctx.send(f"📋 **Son {saat} Saatin Sohbet Özeti:**\n\n{ozet_metni}")
        else:
            raise son_hata

    except Exception as e:
        await ctx.send(f"Özet oluşturulurken bir hata oluştu. Hata: `{e}`")
        print(f"Hata detayı: {e}")

bot.run(DISCORD_TOKEN)
