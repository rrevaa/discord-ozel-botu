import os
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
    print(f"✅ {bot.user} başarıyla giriş yaptı ve GitHub Actions üzerinde aktif!")

@bot.command(name="ozet")
async def ozet(ctx, saat: int = 2):
    # Saat aralığı kontrolü
    if saat < 1 or saat > 5:
        await ctx.send("Lütfen 1 ile 5 arasında bir saat değeri girin (Örn: `!ozet 2`).")
        return

    await ctx.send(f"⏳ Son {saat} saat içerisindeki sohbet taranıyor✨...")

    # Zaman sınırını ayarla (UTC)
    zaman_siniri = datetime.now(timezone.utc) - timedelta(hours=saat)
    mesaj_gecmisi = []

    # Son mesajları kanaldan çek
    async for message in ctx.channel.history(limit=500, after=zaman_siniri):
        if message.author.bot:
            continue
        yazan = message.author.display_name
        icerik = message.clean_content
        mesaj_gecmisi.append(f"{yazan}: {icerik}")

    if not mesaj_gecmisi:
        await ctx.send(f"Son {saat} saat içinde özetlenecek herhangi bir kullanıcı mesajı bulunamadı.")
        return

    sohbet_metni = "\n".join(mesaj_gecmisi)

    # Gemini'ye gönderilecek yönlendirme metni
    prompt = (
        "Sen bir Discord topluluk asistanısın. Sana verilen sohbet geçmişinin "
        "geniş, anlaşılır ve derli toplu bir özetini çıkar.\n"
        "ÖNEMLİ KURALLAR:\n"
        "1. Kesinlikle kullanıcıları etiketleme (@mention yapma), sadece isimlerini düz metin olarak an.\n"
        "2. Önemli konuları, alınan kararları ve öne çıkan sohbet başlıklarını maddeler halinde sun.\n\n"
        f"İşte son {saat} saatin sohbet geçmişi:\n\n{sohbet_metni}"
    )

    try:
        # Gemini 2.5 Flash modeli ile özeti üret
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        ozet_metni = response.text

        # Discord 2000 karakter sınırına göre mesajı bölüp gönder
        if len(ozet_metni) > 1900:
            for chunk in [ozet_metni[i:i+1900] for i in range(0, len(ozet_metni), 1900)]:
                await ctx.send(chunk)
        else:
            await ctx.send(f"📋 **Son {saat} Saatin Sohbet Özeti:**\n\n{ozet_metni}")

    except Exception as e:
        await ctx.send("Özet oluşturulurken bir hata meydana geldi.")
        print(f"Hata detayı: {e}")

# Botu çalıştır (Token ortam değişkeninden çekilir)
bot.run(DISCORD_TOKEN)
