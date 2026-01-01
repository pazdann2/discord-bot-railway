import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
from datetime import datetime
import asyncio
import sys

# 🔴 WPISZ SWÓJ TOKEN
TOKEN = "DISCORD_TOKEN"

# ID kanałów
FREE_SIGN_ID = 1454213320977551462
TRANSFERS_ID = 1453884602312556667
RANKING_CHANNEL_ID = 1454236491222876274

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

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# FUNKCJE EKONOMICZNE
def init_db():
    conn = sqlite3.connect('clubs.db')
    c = conn.cursor()
    
    # Kluby
    c.execute('''CREATE TABLE IF NOT EXISTS clubs 
                 (club_name TEXT PRIMARY KEY, balance INTEGER DEFAULT 0, manager_role TEXT)''')
    
    # Gracze
    c.execute('''CREATE TABLE IF NOT EXISTS players 
                 (player_id TEXT, player_name TEXT, current_club TEXT, value INTEGER DEFAULT 1000,
                  is_transfer_listed BOOLEAN DEFAULT 0, transfer_price INTEGER, 
                  listed_by TEXT, listed_at DATETIME)''')
    
    # Transakcje
    c.execute('''CREATE TABLE IF NOT EXISTS transactions 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, club_from TEXT, club_to TEXT, 
                  amount INTEGER, reason TEXT, timestamp DATETIME, player_name TEXT)''')
    
    # Domyślne saldo 50000 dla każdego klubu
    for club in CLUBS.values():
        c.execute('''INSERT OR IGNORE INTO clubs (club_name, manager_role, balance) 
                     VALUES (?, ?, ?)''', (club['name'], club['manager'], 50000))
    
    conn.commit()
    conn.close()
    print("✅ Baza danych z ekonomią gotowa")

async def update_saldo_channel(club_id: str):
    """Aktualizuj kanał salda dla klubu"""
    if club_id not in CLUBS:
        return
    
    club = CLUBS[club_id]
    channel = bot.get_channel(club['saldo_id'])
    
    if not channel:
        print(f"❌ Nie znaleziono kanału saldo dla {club['name']} (ID: {club['saldo_id']})")
        return
    
    # Pobierz saldo z bazy
    conn = sqlite3.connect('clubs.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM clubs WHERE club_name = ?", (club['name'],))
    result = c.fetchone()
    balance = result[0] if result else 50000
    conn.close()
    
    try:
        # Usuń stare wiadomości bota
        deleted = 0
        async for message in channel.history(limit=20):
            if message.author == bot.user:
                await message.delete()
                deleted += 1
                await asyncio.sleep(0.5)
        
        if deleted > 0:
            print(f"✅ Usunięto {deleted} starych wiadomości z kanału {club['name']}")
    except:
        pass
    
    # Wyślij nowe saldo
    embed = discord.Embed(
        title=f"💰 SALDO: {club['name']}",
        description=f"**Aktualne saldo:** `${balance:,}`",
        color=club['color'],
        timestamp=datetime.now()
    )
    embed.add_field(name="👨‍💼 Prezes", value=f"`{club['manager']}`", inline=True)
    embed.set_footer(text="🔄 Aktualizowane automatycznie")
    
    try:
        await channel.send(embed=embed)
        print(f"✅ Zaktualizowano saldo dla {club['name']}: ${balance:,}")
    except Exception as e:
        print(f"❌ Błąd wysyłania saldo dla {club['name']}: {e}")

async def update_ranking_channel():
    """Aktualizuj kanał rankingu"""
    channel = bot.get_channel(RANKING_CHANNEL_ID)
    
    if not channel:
        print(f"❌ Nie znaleziono kanału rankingu (ID: {RANKING_CHANNEL_ID})")
        return
    
    # Pobierz dane z bazy
    conn = sqlite3.connect('clubs.db')
    c = conn.cursor()
    c.execute("SELECT club_name, balance FROM clubs ORDER BY balance DESC")
    clubs = c.fetchall()
    conn.close()
    
    try:
        # Usuń stare wiadomości bota
        deleted = 0
        async for message in channel.history(limit=20):
            if message.author == bot.user:
                await message.delete()
                deleted += 1
                await asyncio.sleep(0.5)
        
        if deleted > 0:
            print(f"✅ Usunięto {deleted} starych wiadomości z rankingu")
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
    
    # Wyślij ranking
    try:
        await channel.send(embed=embed)
        print(f"✅ Zaktualizowano ranking ({len(unique_clubs)} klubów)")
    except Exception as e:
        print(f"❌ Błąd wysyłania rankingu: {e}")

async def update_all_saldo_channels():
    """Aktualizuj wszystkie kanały salda"""
    print("🔄 Aktualizowanie wszystkich kanałów salda...")
    for club_id in CLUBS.keys():
        await update_saldo_channel(club_id)
        await asyncio.sleep(1)  # Poczekaj 1 sekundę między aktualizacjami
    print("✅ Wszystkie kanały salda zaktualizowane")

# KOMENDY EKONOMICZNE
@bot.tree.command(name="dodaj_kase", description="Dodaj kasę klubowi (tylko admin)")
@app_commands.describe(klub="Wybierz klub", kwota="Kwota do dodania", powód="Powód (np. wygrany mecz)")
@app_commands.choices(klub=[
    app_commands.Choice(name="Wisła Kraków", value="wislakrakow"),
    app_commands.Choice(name="Santos", value="santos"),
    app_commands.Choice(name="Bażant Strzałkowo", value="bazant"),
    app_commands.Choice(name="As Roma", value="asroma"),
    app_commands.Choice(name="UKS Kolorado", value="ukskolorado"),
    app_commands.Choice(name="Chelsea", value="chelsea"),
    app_commands.Choice(name="Fc Barcelona", value="fcbarcelona"),
    app_commands.Choice(name="Juventus", value="juventus"),
])
async def dodaj_kase(interaction: discord.Interaction, klub: str, kwota: int, powód: str):
    """Dodaj kasę klubowi"""
    
    # Sprawdź uprawnienia (Owner, Admin, Zarząd)
    allowed_roles = ["Owner", "Admin", "Zarząd"]
    if not any(role.name in allowed_roles for role in interaction.user.roles):
        await interaction.response.send_message(
            "❌ Brak uprawnień! Wymagana rola: Owner, Admin lub Zarząd",
            ephemeral=True
        )
        return
    
    if klub not in CLUBS:
        await interaction.response.send_message("❌ Nieznany klub!", ephemeral=True)
        return
    
    club = CLUBS[klub]
    
    # Dodaj kasę w bazie
    conn = sqlite3.connect('clubs.db')
    c = conn.cursor()
    
    # Pobierz stare saldo
    c.execute("SELECT balance FROM clubs WHERE club_name = ?", (club['name'],))
    old_balance = c.fetchone()[0]
    
    # Zaktualizuj saldo
    c.execute("UPDATE clubs SET balance = balance + ? WHERE club_name = ?", 
              (kwota, club['name']))
    
    # Pobierz nowe saldo
    c.execute("SELECT balance FROM clubs WHERE club_name = ?", (club['name'],))
    new_balance = c.fetchone()[0]
    
    # Dodaj transakcję do historii
    c.execute('''INSERT INTO transactions (club_from, club_to, amount, reason, timestamp) 
                 VALUES (?, ?, ?, ?, ?)''',
                 ("SYSTEM", club['name'], kwota, powód, datetime.now()))
    
    conn.commit()
    conn.close()
    
    # Wyślij potwierdzenie
    embed = discord.Embed(
        title="💸 DODANO KASĘ",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    embed.add_field(name="Klub", value=club['name'], inline=True)
    embed.add_field(name="Kwota", value=f"`+${kwota:,}`", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    embed.add_field(name="Stare saldo", value=f"`${old_balance:,}`", inline=True)
    embed.add_field(name="Nowe saldo", value=f"`${new_balance:,}`", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    embed.add_field(name="Powód", value=powód, inline=False)
    embed.add_field(name="Dodał", value=interaction.user.mention, inline=True)
    
    await interaction.response.send_message(embed=embed)
    
    # Aktualizuj kanały
    await update_saldo_channel(klub)
    await update_ranking_channel()
    
    print(f"✅ Dodano ${kwota:,} do {club['name']} (teraz: ${new_balance:,})")

@bot.tree.command(name="saldo", description="Sprawdź saldo klubu")
@app_commands.describe(klub="Wybierz klub")
@app_commands.choices(klub=[
    app_commands.Choice(name="Wisła Kraków", value="wislakrakow"),
    app_commands.Choice(name="Santos", value="santos"),
    app_commands.Choice(name="Bażant Strzałkowo", value="bazant"),
    app_commands.Choice(name="As Roma", value="asroma"),
    app_commands.Choice(name="UKS Kolorado", value="ukskolorado"),
    app_commands.Choice(name="Chelsea", value="chelsea"),
    app_commands.Choice(name="Fc Barcelona", value="fcbarcelona"),
    app_commands.Choice(name="Juventus", value="juventus"),
])
async def saldo(interaction: discord.Interaction, klub: str):
    """Sprawdź saldo klubu"""
    if klub not in CLUBS:
        await interaction.response.send_message("❌ Nieznany klub!", ephemeral=True)
        return
    
    club = CLUBS[klub]
    
    # Pobierz saldo z bazy
    conn = sqlite3.connect('clubs.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM clubs WHERE club_name = ?", (club['name'],))
    result = c.fetchone()
    balance = result[0] if result else 50000
    conn.close()
    
    embed = discord.Embed(
        title=f"💰 SALDO: {club['name']}",
        color=club['color'],
        timestamp=datetime.now()
    )
    embed.add_field(name="Saldo", value=f"**`${balance:,}`**", inline=False)
    embed.add_field(name="Prezes", value=f"`{club['manager']}`", inline=True)
    embed.set_footer(text=f"Sprawdzone przez {interaction.user.display_name}")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="aktualizuj_kanały", description="Aktualizuj wszystkie kanały (tylko admin)")
async def aktualizuj_kanały(interaction: discord.Interaction):
    """Ręczna aktualizacja kanałów"""
    allowed_roles = ["Owner", "Admin", "Zarząd"]
    if not any(role.name in allowed_roles for role in interaction.user.roles):
        await interaction.response.send_message("❌ Brak uprawnień!", ephemeral=True)
        return
    
    await interaction.response.send_message("🔄 Aktualizuję wszystkie kanały...")
    
    # Aktualizuj kanały
    await update_all_saldo_channels()
    await update_ranking_channel()
    
    await interaction.followup.send("✅ Wszystkie kanały zaktualizowane!")

# Reszta komend (dodaj, usun, ranking, ping, sync) - zostaw bez zmian z poprzedniego kodu

@bot.event
async def on_ready():
    print("="*60)
    print(f"✅ Bot: {bot.user}")
    print(f"✅ ID: {bot.user.id}")
    print("="*60)
    
    # Inicjalizuj bazę z ekonomią
    init_db()
    
    # Sync komend
    try:
        synced = await bot.tree.sync()
        print(f"✅ Zsynchrowano {len(synced)} komend")
        print(f"✅ Komendy ekonomiczne: /dodaj_kase, /saldo, /aktualizuj_kanały")
    except Exception as e:
        print(f"⚠️ Błąd sync: {e}")
    
    # Aktualizuj kanały po starcie
    print("🔄 Aktualizowanie kanałów po starcie...")
    await update_all_saldo_channels()
    await update_ranking_channel()
    
    print("🤖 Bot z ekonomią gotowy do działania!")

# Uruchomienie
if __name__ == "__main__":
    print("🚀 Uruchamianie bota z ekonomią...")
    
    if not TOKEN or TOKEN == "DISCORD_TOKEN":
        print("❌ WPISZ SWÓJ TOKEN W LINIJCE 10!")
        sys.exit(1)
    
    try:
        bot.run(TOKEN)
    except discord.errors.LoginFailure:
        print("❌ TOKEN NIEPOPRAWNY! Zresetuj w Discord Dev Portal")
    except Exception as e:
        print(f"❌ Błąd: {e}")