import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
from datetime import datetime
import asyncio
import os
import sys

# Token z Environment Variables (Render)
TOKEN = os.getenv("DISCORD_TOKEN")

# Jeśli brak tokena - wyłącz bot
if not TOKEN:
    print("❌ BRAK TOKENA! Dodaj DISCORD_TOKEN w Environment Variables na Render")
    print("❌ Przejdź do: Render → Twój service → Environment")
    print("❌ Dodaj: DISCORD_TOKEN = twój_token_z_discord_dev_portal")
    sys.exit(1)

# ID kanałów (zmień na swoje!)
FREE_SIGN_ID = 1454213320977551462
TRANSFERS_ID = 1453884602312556667
RANKING_CHANNEL_ID = 1454236491222876274

# Konfiguracja klubów
CLUBS = {
    "wislakrakow": {
        "name": "Wisła Kraków",
        "manager": "Prezes Wisły",
        "color": discord.Color.red(),
        "saldo_id": 1454212839144427754,
        "transfer_id": 1454214931397476534
    },
    "santos": {
        "name": "Santos",
        "manager": "Prezes Santos",
        "color": discord.Color.dark_purple(),
        "saldo_id": 1454212811348508732,
        "transfer_id": 1454215000905482331
    },
    "bazant": {
        "name": "Bażant Strzałkowo",
        "manager": "Prezes Bażanta",
        "color": discord.Color.green(),
        "saldo_id": 1454212880571564043,
        "transfer_id": 1454215083939860523
    },
    "asroma": {
        "name": "As Roma",
        "manager": "Prezes Roma",
        "color": discord.Color.dark_red(),
        "saldo_id": 1454212870370758793,
        "transfer_id": 1454215058006741085
    },
    "ukskolorado": {
        "name": "UKS Kolorado",
        "manager": "Prezes Kolorado",
        "color": discord.Color.blue(),
        "saldo_id": 1454212866289828030,
        "transfer_id": 1454215100071411945
    },
    "chelsea": {
        "name": "Chelsea",
        "manager": "Prezes Chelsea",
        "color": discord.Color.dark_blue(),
        "saldo_id": 1454212851052052652,
        "transfer_id": 1454215044610130071
    },
    "fcbarcelona": {
        "name": "Fc Barcelona",
        "manager": "Prezes Fc Barcelony",
        "color": discord.Color.dark_gold(),
        "saldo_id": 1454212885512192162,
        "transfer_id": 1454215070845239456
    },
    "juventus": {
        "name": "Juventus",
        "manager": "Prezes Juventusu",
        "color": discord.Color.from_rgb(0, 0, 0),
        "saldo_id": 1454212832160645305,
        "transfer_id": 1454215028478837019
    }
}

# Inicjalizacja bota
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Funkcje pomocnicze
def init_db():
    """Inicjalizacja bazy danych"""
    try:
        conn = sqlite3.connect('clubs.db')
        c = conn.cursor()
        
        # Tabele
        c.execute('''CREATE TABLE IF NOT EXISTS clubs (
            club_name TEXT PRIMARY KEY, 
            balance INTEGER DEFAULT 0, 
            manager_role TEXT)''')
            
        c.execute('''CREATE TABLE IF NOT EXISTS players (
            player_id TEXT, 
            player_name TEXT, 
            current_club TEXT, 
            value INTEGER DEFAULT 1000, 
            is_transfer_listed BOOLEAN DEFAULT 0, 
            transfer_price INTEGER, 
            listed_by TEXT, 
            listed_at DATETIME)''')
            
        c.execute('''CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            club_from TEXT, 
            club_to TEXT, 
            amount INTEGER, 
            reason TEXT, 
            timestamp DATETIME, 
            player_name TEXT)''')
        
        # Domyślne dane klubów
        for club in CLUBS.values():
            c.execute('''INSERT OR IGNORE INTO clubs (club_name, manager_role, balance) 
                         VALUES (?, ?, ?)''', 
                         (club['name'], club['manager'], 50000))
        
        conn.commit()
        conn.close()
        print("✅ Baza danych zainicjalizowana")
    except Exception as e:
        print(f"❌ Błąd bazy danych: {e}")

async def update_saldo_channel(club_id):
    """Aktualizacja kanału salda"""
    if club_id not in CLUBS:
        return
    
    config = CLUBS[club_id]
    saldo_channel = bot.get_channel(config['saldo_id'])
    
    if not saldo_channel:
        print(f"❌ Nie znaleziono kanału saldo dla {config['name']}")
        return
    
    try:
        conn = sqlite3.connect('clubs.db')
        c = conn.cursor()
        c.execute("SELECT balance FROM clubs WHERE club_name = ?", (config['name'],))
        result = c.fetchone()
        balance = result[0] if result else 0
        conn.close()
        
        # Usuń stare wiadomości bota
        try:
            async for message in saldo_channel.history(limit=10):
                if message.author == bot.user:
                    await message.delete()
        except:
            pass
        
        # Wyślij nowe saldo
        embed = discord.Embed(
            title=f"💰 SALDO: {config['name']}",
            description=f"**Saldo:** `${balance:,}`",
            color=config['color'],
            timestamp=datetime.now()
        )
        embed.add_field(name="👨‍💼 Prezes", value=f"`{config['manager']}`", inline=True)
        embed.set_footer(text="🔄 Aktualizowane automatycznie")
        await saldo_channel.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Błąd aktualizacji saldo: {e}")

async def update_ranking_channel():
    """Aktualizacja kanału rankingu"""
    ranking_channel = bot.get_channel(RANKING_CHANNEL_ID)
    
    if not ranking_channel:
        print("❌ Nie znaleziono kanału rankingu!")
        return
    
    try:
        conn = sqlite3.connect('clubs.db')
        c = conn.cursor()
        c.execute("SELECT club_name, balance FROM clubs ORDER BY balance DESC")
        clubs = c.fetchall()
        conn.close()
        
        # Usuń stare wiadomości
        try:
            async for message in ranking_channel.history(limit=10):
                if message.author == bot.user:
                    await message.delete()
        except:
            pass
        
        # Stwórz ranking
        embed = discord.Embed(
            title="🏆 RANKING KLUBÓW",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]
        
        # Usuń duplikaty
        seen = set()
        unique_clubs = []
        for name, bal in clubs:
            if name not in seen:
                seen.add(name)
                unique_clubs.append((name, bal))
        
        # Dodaj do embeda
        for idx, (name, bal) in enumerate(unique_clubs[:8]):
            medal = medals[idx] if idx < len(medals) else f"{idx+1}."
            embed.add_field(
                name=f"{medal} {name}",
                value=f"**${bal:,}**",
                inline=False
            )
        
        await ranking_channel.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Błąd aktualizacji rankingu: {e}")

async def update_all_channels():
    """Aktualizacja wszystkich kanałów"""
    print("🔄 Aktualizowanie kanałów...")
    for club_id in CLUBS.keys():
        await update_saldo_channel(club_id)
        await asyncio.sleep(0.5)
    await update_ranking_channel()
    print("✅ Wszystkie kanały zaktualizowane!")

# Eventy bota
@bot.event
async def on_ready():
    """Bot gotowy"""
    print("="*50)
    print(f"✅ Bot zalogowany jako: {bot.user}")
    print(f"✅ ID: {bot.user.id}")
    print(f"✅ Ping: {round(bot.latency * 1000)}ms")
    print("="*50)
    
    # Inicjalizacja bazy
    init_db()
    
    # Sync komend
    try:
        synced = await bot.tree.sync()
        print(f"✅ Zsynchrowano {len(synced)} komend slash")
    except Exception as e:
        print(f"❌ Błąd sync komend: {e}")
    
    # Aktualizuj kanały
    await update_all_channels()
    
    print("🤖 Bot działa poprawnie na Render!")

# Komendy slash
@bot.tree.command(name="sync", description="Ręczna synchronizacja komend (tylko admin)")
async def sync(interaction: discord.Interaction):
    """Ręczny sync komend"""
    if interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🔄 Synchronizacja komend...")
        try:
            synced = await bot.tree.sync()
            await interaction.followup.send(f"✅ Zsynchrowano {len(synced)} komend")
        except Exception as e:
            await interaction.followup.send(f"❌ Błąd: {e}")
    else:
        await interaction.response.send_message("❌ Brak uprawnień!", ephemeral=True)

@bot.tree.command(name="ping", description="Sprawdź ping bota")
async def ping(interaction: discord.Interaction):
    """Komenda ping"""
    await interaction.response.send_message(f"🏓 Pong! {round(bot.latency * 1000)}ms")

@bot.tree.command(name="ranking", description="Pokaż ranking klubów")
async def ranking(interaction: discord.Interaction):
    """Wyświetl ranking"""
    try:
        conn = sqlite3.connect('clubs.db')
        c = conn.cursor()
        c.execute("SELECT club_name, balance FROM clubs ORDER BY balance DESC")
        clubs = c.fetchall()
        conn.close()
        
        embed = discord.Embed(
            title="🏆 RANKING KLUBÓW",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]
        
        seen = set()
        unique_clubs = []
        for name, bal in clubs:
            if name not in seen:
                seen.add(name)
                unique_clubs.append((name, bal))
        
        for idx, (name, bal) in enumerate(unique_clubs[:8]):
            medal = medals[idx] if idx < len(medals) else f"{idx+1}."
            embed.add_field(
                name=f"{medal} {name}",
                value=f"**${bal:,}**",
                inline=False
            )
        
        if len(unique_clubs) > 8:
            other_text = "\n".join([
                f"{idx+9}. {name}: ${bal:,}" 
                for idx, (name, bal) in enumerate(unique_clubs[8:])
            ])
            embed.add_field(name="📊 Pozostałe", value=other_text, inline=False)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Błąd: {e}", ephemeral=True)

# Pozostałe komendy z twojego kodu...
# (TUTAJ WKLEJ RESZTĘ SWOICH KOMEND: dodaj, usun, wystaw, kup, etc.)

# Uruchomienie bota
if __name__ == "__main__":
    print("🚀 Uruchamianie bota klubów piłkarskich...")
    print(f"📊 Ilość klubów: {len(CLUBS)}")
    print(f"🔑 Token: {'*' * len(TOKEN) if TOKEN else 'BRAK'}")
    
    if not TOKEN:
        print("❌ PRZERWANO: Brak tokena Discord")
        print("ℹ️ Dodaj DISCORD_TOKEN w Environment Variables na Render")
    else:
        try:
            bot.run(TOKEN)
        except discord.errors.LoginFailure:
            print("❌ BŁĄD LOGOWANIA: Nieprawidłowy token Discord")
            print("ℹ️ Sprawdź czy token jest poprawny w Discord Dev Portal")
        except Exception as e:
            print(f"❌ NIESPODZIEWANY BŁĄD: {e}")