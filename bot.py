import os
import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from google import genai

# 1. API anahtarlarını çek
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Gemini istemcisi
gemini_client = genai.Client(api_key=GEMINI_KEY)

# Discord Bot ayarları
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} başarıyla bağlandı ve hazır!")

@bot.command(name="ozet")
async def ozet(ctx, saat: int = 2):
    if saat < 1 or saat > 5:
        await ctx.send("Lütfen 1 ile 5 arasında bir saat değeri girin (Örn: `!ozet 2`).")
        return

    await ctx.send(f"⏳ Son {saat} saat içerisindeki sohbet taranıyor✨...")

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

        # Gemini 2.5 Flash ile özet oluştur
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        ozet_metni = response.text

        if len(ozet_metni) > 1900:
            for chunk in [ozet_metni[i:i+1900] for i in range(0, len(ozet_metni), 1900)]:
                await ctx.send(chunk)
        else:
            await ctx.send(f"📋 **Son {saat} Saatin Sohbet Özeti:**\n\n{ozet_metni}")

    except Exception as e:
        await ctx.send(f"Özet oluşturulurken bir hata oluştu. Hata: `{e}`")
        print(f"Hata detayı: {e}")

bot.run(DISCORD_TOKEN)
