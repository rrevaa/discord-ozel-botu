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

# Bot hazır olduğunda çalışacak event
@bot.event
async def on_ready():
    print(f"✅ {bot.user} başarıyla bağlandı ve aktif!")

# ---------------------------------------------------------
# GEMINI İLE SOHBET ÖZETLEME KOMUTU (!ozet 1-12)
# ---------------------------------------------------------
@bot.command(name="ozet")
async def ozet(ctx, saat: int = 2):
    # Limit 1 ile 12 saat arasında ayarlandı
    if saat < 1 or saat > 12:
        await ctx.send("Lütfen 1 ile 12 arasında bir saat değeri girin (Örn: `!ozet 6`).")
        return

    await ctx.send(f"⏳ Son {saat} saat içerisindeki sohbet hemmmmeeenn taranıyor, taranan mesaj sayısına bağlı olarak işlem birazcık, çok azıcık uzayabilir✨..."")

    zaman_siniri = datetime.now(timezone.utc) - timedelta(hours=saat)
    mesaj_gecmisi = []

    try:
        # Son mesajları kanaldan çek (Limit 1800)
        async for message in ctx.channel.history(limit=1800, after=zaman_siniri):
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

        # Güncel ve aktif Gemini modelleri
        models_to_try = ["gemini-3.6-flash", "gemini-3.6-pro"]
        ozet_metni = None
        son_hata = None

        for model_name in models_to_try:
            for deneme in range(3):  # Her model için 3 defa dene
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
                        # 503 hatasında bekleme süresini kademeli artır (2s, 4s, 6s)
                        await asyncio.sleep((deneme + 1) * 2)
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
