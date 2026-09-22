import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from google import genai

# 1. GEMINI API ANAHTARINIZI BURAYA YAZIN
gemini_client = genai.Client(api_key="AQ.Ab8RN6KzbBf_JhkETZBtBNKkyTOKitinMu7Ijtg8ok26RNveTA")

# Discord Bot Yetkileri
intents = discord.Intents.default()
intents.message_content = True  # Mesaj okuma izni
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} olarak başarıyla giriş yapıldı! Bot aktif.")

@bot.command(name="ozet")
async def ozet(ctx, saat: int = 2):
    """
    Belirtilen saat aralığındaki (1-5 saat) mesajların özetini çıkarır.
    Kullanımı: !ozet 3
    """
    if saat < 1 or saat > 5:
        await ctx.send("Lütfen 1 ile 5 arasında bir saat değeri girin (Örn: `!ozet 2`).")
        return

    await ctx.send(f"⏳ Son {saat} saat içerisindeki sohbet taranıyor...")

    # Zaman aralığı (UTC)
    zaman_siniri = datetime.now(timezone.utc) - timedelta(hours=saat)
    mesaj_gecmisi = []

    # Mesajları okuma
    async for message in ctx.channel.history(limit=500, after=zaman_siniri):
        if message.author.bot:
            continue  # Bot mesajlarını atla
        
        yazan = message.author.display_name
        icerik = message.clean_content  # Bildirim atmaması için düz metne çevirir
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

    try:
        response = gemini_client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
        )

        ozet_metni = response.text

        # Discord 2000 karakter sınırına karşı mesajı bölme
        if len(ozet_metni) > 1900:
            for chunk in [ozet_metni[i:i+1900] for i in range(0, len(ozet_metni), 1900)]:
                await ctx.send(chunk)
        else:
            await ctx.send(f"📋 **Son {saat} Saatin Sohbet Özeti:**\n\n{ozet_metni}")

    except Exception as e:
        await ctx.send("Özet oluşturulurken bir hata meydana geldi.")
        print(f"Hata: {e}")

# 2. DISCORD BOT TOKENINIZI BURAYA YAZIN
bot.run("MTU1MjAwMjMzODQyMjUzMDA0OA.GvwW1w.9dOCr73ZefsVw5yj5Vnov2zYeNvhruEC8-qUTM")