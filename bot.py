import os
import asyncio
import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from groq import Groq

# ---------------------------------------------------------
# 1. API VE KANAL AYARLARI
# ---------------------------------------------------------
GROQ_KEY = os.getenv("GROQ_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# ID'leri buraya girin:
GENEL_CHAT_KANAL_ID = 1368566503372492883  # Özetlenecek sohbet kanalı
BOT_KOMUT_KANAL_ID = 1368582404763156512   # Botun SADECE çalışacağı komut kanalı

groq_client = Groq(api_key=GROQ_KEY)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------------------------------------------------
# 2. EVENT VE YARDIMCI FONKSİYONLAR
# ---------------------------------------------------------
@bot.event
async def on_ready():
    print(f"✅ Özet Botu Aktif: {bot.user}")

def ask_groq_sync(prompt: str) -> str:
    completion = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=1000,
    )
    return completion.choices[0].message.content

# ---------------------------------------------------------
# 3. ÖZET KOMUTU (!ozet)
# ---------------------------------------------------------
@bot.command(name="ozet")
async def ozet(ctx, saat: int = 2):
    # KANAL KONTROLÜ: Komut belirlenen bot kanalı dışında yazıldıysa engelle
    if ctx.channel.id != BOT_KOMUT_KANAL_ID:
        await ctx.send(f"⚠️ Bu komut sadece <#{BOT_KOMUT_KANAL_ID}> kanalında kullanılabilir.", delete_after=10)
        return

    if saat < 1 or saat > 12:
        await ctx.send("Lütfen 1 ila 12 arasında bir saat değeri belirtin (Örn: `!ozet 4`).")
        return

    # Okunacak kanal: Genel Chat
    genel_kanal = bot.get_channel(GENEL_CHAT_KANAL_ID)

    if not genel_kanal:
        await ctx.send("❌ Genel sohbet kanalı bulunamadı. Lütfen `GENEL_CHAT_KANAL_ID` değerini kontrol edin.")
        return

    await ctx.send(f"⏳ <#{genel_kanal.id}> kanalındaki son {saat} saatin sohbeti inceleniyor✨...")

    zaman_siniri = datetime.now(timezone.utc) - timedelta(hours=saat)
    mesaj_gecmisi = []

    try:
        # Genel chat kanalının geçmişi taranıyor
        async for message in genel_kanal.history(limit=1800, after=zaman_siniri):
            if message.author.bot:
                continue
            yazan = message.author.display_name
            icerik = message.clean_content
            if icerik.strip():
                mesaj_gecmisi.append(f"{yazan}: {icerik}")

        if not mesaj_gecmisi:
            await ctx.send(f"<#{genel_kanal.id}> kanalında son {saat} saatte yazılmış mesaj bulunamadı.")
            return

        sohbet_metni = "\n".join(mesaj_gecmisi)

        prompt = (
            "GÖREV: Sana verilen Discord genel sohbet geçmişini samimi, anlaşılır ve düzenli bir dille özetle.\n"
            "KURALLAR:\n"
            "1. Kullanıcıları etiketleme (@mention yapma), isimlerini düz metin yaz.\n"
            "2. Önemli konuları ve öne çıkan sohbet başlıklarını maddeler halinde sun.\n\n"
            f"Son {saat} saatin genel chat sohbeti:\n\n{sohbet_metni}"
        )

        ozet_metni = await asyncio.to_thread(ask_groq_sync, prompt)

        if ozet_metni:
            if len(ozet_metni) > 1900:
                for chunk in [ozet_metni[i:i+1900] for i in range(0, len(ozet_metni), 1900)]:
                    await ctx.send(chunk)
            else:
                await ctx.send(f"📋 **<#{genel_kanal.id}> Kanalı Son {saat} Saatin Özeti:**\n\n{ozet_metni}")
        else:
            await ctx.send("Özet oluşturulurken bir hata oluştu.")

    except Exception as e:
        await ctx.send(f"Bir hata oluştu: `{e}`")

bot.run(DISCORD_TOKEN)
