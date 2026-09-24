import os
import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------
# 1. AYARLAR VE TOKEN
# ---------------------------------------------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Kanal ID'leri
GENEL_CHAT_KANAL_ID = 123456789012345678  # Mesajların okunacağı genel sohbet kanalı
BOT_KOMUT_KANAL_ID = 876543210987654321   # Botun çalışacağı komut kanalı

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------------------------------------------------
# 2. EVENTLER
# ---------------------------------------------------------
@bot.event
async def on_ready():
    print(f"✅ Bot başarıyla giriş yaptı: {bot.user}")

# ---------------------------------------------------------
# 3. SADE ÖZET / MESAJ GETİRME KOMUTU
# ---------------------------------------------------------
@bot.command(name="ozet")
async def ozet(ctx, saat: int = 2):
    # Komutun sadece bot kanalında çalışmasını sağlayan kontrol
    if ctx.channel.id != BOT_KOMUT_KANAL_ID:
        await ctx.send(f"⚠️ Bu komut sadece <#{BOT_KOMUT_KANAL_ID}> kanalında kullanılabilir.", delete_after=10)
        return

    if saat < 1 or saat > 12:
        await ctx.send("Lütfen 1 ile 12 arasında bir saat değeri belirtin (Örn: `!ozet 4`).")
        return

    genel_kanal = bot.get_channel(GENEL_CHAT_KANAL_ID)

    if not genel_kanal:
        await ctx.send("❌ Genel sohbet kanalı bulunamadı. Lütfen `GENEL_CHAT_KANAL_ID` değerini kontrol edin.")
        return

    await ctx.send(f"⏳ <#{genel_kanal.id}> kanalındaki son {saat} saatin mesajları toplanıyor...")

    zaman_siniri = datetime.now(timezone.utc) - timedelta(hours=saat)
    mesaj_gecmisi = []

    try:
        # Genel chat kanalının geçmişini tarama
        async for message in genel_kanal.history(limit=1800, after=zaman_siniri):
            if message.author.bot:
                continue
            yazan = message.author.display_name
            icerik = message.clean_content
            if icerik.strip():
                mesaj_gecmisi.append(f"**{yazan}**: {icerik}")

        if not mesaj_gecmisi:
            await ctx.send(f"<#{genel_kanal.id}> kanalında son {saat} saatte yazılmış mesaj bulunamadı.")
            return

        # AI olmadan doğrudan mesajları sıralayıp gönderme
        ham_metin = "\n".join(mesaj_gecmisi)
        
        if len(ham_metin) > 1900:
            for chunk in [ham_metin[i:i+1900] for i in range(0, len(ham_metin), 1900)]:
                await ctx.send(chunk)
        else:
            await ctx.send(f"📋 **<#{genel_kanal.id}> Son {saat} Saatin Mesaj Akışı:**\n\n{ham_metin}")

    except Exception as e:
        await ctx.send(f"Bir hata oluştu: `{e}`")

bot.run(DISCORD_TOKEN)
