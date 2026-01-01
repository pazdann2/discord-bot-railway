import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
from datetime import datetime
import asyncio
import os
import sys

# ========== KONFIGURACJA ==========
# 🔴 DLA RENDER/RAILWAY/HOSTINGU:
TOKEN = os.getenv("DISCORD_TOKEN")

# ID kanałów Discord
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

# ========== BAZA DANYCH ==========
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
        
        # Domyślne dane
        for club in CLUBS.values():
            c.execute('''INSERT OR IGNORE INTO clubs (club_name, manager_role, balance) 
                         VALUES (?, ?, ?)''', (club['name'], club['manager'], 50000))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Błąd bazy: {e}")
        return False

# ========== FUNKCJE POMOCNICZE ==========
async def update_saldo_channel(club_id: str):
    """Aktualizuj kanał salda klubu"""
    if club_id not in CLUBS:
        return
    
    club = CLUBS[club_id]
    channel = bot.get_channel(club['saldo_id'])
    
    if not channel:
        print(f"❌ Brak kanału: {club['name']} (ID: {club['saldo_id']})")
        return
    
    # Pobierz saldo
    conn = sqlite3.connect('clubs.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM clubs WHERE club_name = ?", (club['name'],))
    result = c.fetchone()
    balance = result[0] if result else 50000
    conn.close()
    
    # Usuń stare wiadomości bota
    try:
        async for message in channel.history(limit=10):
            if message.author == bot.user:
                await message.delete()
    except:
        pass
    
    # Wyślij nowe saldo
    embed = discord.Embed(
        title=f"💰 SALDO: {club['name']}",
        description=f"**Saldo:** `${balance:,}`",
        color=club['color'],
        timestamp=datetime.now()
    )
    embed.add_field(name="👨‍💼 Prezes", value=f"`{club['manager']}`", inline=True)
    embed.set_footer(text="🔄 Aktualizowane automatycznie")
    
    try:
        await channel.send(embed=embed)
    except:
        pass

async def update_ranking_channel():
    """Aktualizuj kanał rankingu"""
    channel = bot.get_channel(RANKING_CHANNEL_ID)
    
    if not channel:
        print(f"❌ Brak kanału rankingu (ID: {RANKING_CHANNEL_ID})")
        return
    
    # Pobierz dane
    conn = sqlite3.connect('clubs.db')
    c = conn.cursor()
    c.execute("SELECT club_name, balance FROM clubs ORDER BY balance DESC")
    clubs = c.fetchall()
    conn.close()
    
    # Usuń stare wiadomości
    try:
        async for message in channel.history(limit=10):
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
    
    # Dodaj do rankingu
    for idx, (name, bal) in enumerate(unique_clubs[:8]):
        medal = medals[idx] if idx < len(medals) else f"{idx+1}."
        embed.add_field(
            name=f"{medal} {name}",
            value=f"**${bal:,}**",
            inline=False
        )
    
    try:
        await channel.send(embed=embed)
    except:
        pass

async def update_all_channels():
    """Aktualizuj wszystkie kanały"""
    print("🔄 Aktualizowanie kanałów...")
    for club_id in CLUBS.keys():
        await update_saldo_channel(club_id)
        await asyncio.sleep(1)
    await update_ranking_channel()
    print("✅ Kanały zaktualizowane")

# ========== EVENTY BOTA ==========
@bot.event
async def on_ready():
    """Bot gotowy do działania"""
    print("="*60)
    print(f"✅ Bot: {bot.user}")
    print(f"✅ ID: {bot.user.id}")
    print("="*60)
    
    # Inicjalizuj bazę
    if init_db():
        print("✅ Baza danych gotowa")
    else:
        print("❌ Błąd bazy danych")
    
    # Sync komend
    try:
        synced = await bot.tree.sync()
        print(f"✅ Zsynchrowano {len(synced)} komend")
    except Exception as e:
        print(f"⚠️ Błąd sync: {e}")
    
    # Aktualizuj kanały
    await update_all_channels()
    
    print("🤖 Bot gotowy!")

# ========== KOMENDY ==========
@bot.tree.command(name="ping", description="Sprawdź ping bota")
async def ping(interaction: discord.Interaction):
    """Komenda ping"""
    await interaction.response.send_message(f"🏓 Pong! {round(bot.latency * 1000)}ms")

@bot.tree.command(name="sync", description="Sync komend (tylko admin)")
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

@bot.tree.command(name="ranking", description="Pokaż ranking klubów")
async def ranking(interaction: discord.Interaction):
    """Wyświetl ranking"""
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
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="dodaj", description="Dodaj gracza do klubu")
@app_commands.describe(gracz="Gracz", klub="Wybierz klub")
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
async def dodaj(interaction: discord.Interaction, gracz: discord.Member, klub: str):
    """Dodaj gracza do klubu"""
    if klub not in CLUBS:
        await interaction.response.send_message("❌ Nieznany klub!", ephemeral=True)
        return
    
    club = CLUBS[klub]
    
    # Sprawdź uprawnienia
    if not any(role.name == club["manager"] for role in interaction.user.roles):
        await interaction.response.send_message(f"❌ Brak roli: {club['manager']}", ephemeral=True)
        return
    
    # Sprawdź czy gracz już w klubie
    conn = sqlite3.connect('clubs.db')
    c = conn.cursor()
    c.execute("SELECT current_club FROM players WHERE player_id = ?", (str(gracz.id),))
    if c.fetchone():
        await interaction.response.send_message(f"❌ {gracz.mention} już w klubie", ephemeral=True)
        conn.close()
        return
    
    # Dodaj gracza
    c.execute('''INSERT INTO players (player_id, player_name, current_club, value) 
                 VALUES (?, ?, ?, ?)''', (str(gracz.id), gracz.display_name, club['name'], 1000))
    
    # Dodaj rolę
    role = discord.utils.get(interaction.guild.roles, name=club['name'])
    if not role:
        role = await interaction.guild.create_role(name=club['name'], color=club['color'])
    await gracz.add_roles(role)
    
    conn.commit()
    conn.close()
    
    await interaction.response.send_message(f"✅ {gracz.mention} dodany do **{club['name']}**")
    
    # Powiadomienie na free sign
    channel = bot.get_channel(FREE_SIGN_ID)
    if channel:
        embed = discord.Embed(
            title="📝 FREE SIGNING",
            description=f"**{club['name']}** podpisał {gracz.mention}",
            color=club['color'],
            timestamp=datetime.now()
        )
        embed.add_field(name="Prezes", value=interaction.user.mention)
        await channel.send(embed=embed)

@bot.tree.command(name="usun", description="Usuń gracza z klubu")
@app_commands.describe(gracz="Gracz")
async def usun(interaction: discord.Interaction, gracz: discord.Member):
    """Usuń gracza z klubu"""
    conn = sqlite3.connect('clubs.db')
    c = conn.cursor()
    
    c.execute("SELECT current_club FROM players WHERE player_id = ?", (str(gracz.id),))
    result = c.fetchone()
    
    if not result:
        await interaction.response.send_message("❌ Gracz nie jest w klubie", ephemeral=True)
        conn.close()
        return
    
    club_name = result[0]
    club_config = next((c for c in CLUBS.values() if c['name'] == club_name), None)
    
    if not club_config:
        await interaction.response.send_message("❌ Błąd: klub nie znaleziony", ephemeral=True)
        conn.close()
        return
    
    # Sprawdź uprawnienia
    if not any(role.name == club_config["manager"] for role in interaction.user.roles):
        await interaction.response.send_message(f"❌ Nie jesteś prezesem {club_name}!", ephemeral=True)
        conn.close()
        return
    
    # Usuń gracza
    c.execute("DELETE FROM players WHERE player_id = ?", (str(gracz.id),))
    
    # Usuń rolę
    role = discord.utils.get(interaction.guild.roles, name=club_name)
    if role and role in gracz.roles:
        await gracz.remove_roles(role)
    
    conn.commit()
    conn.close()
    
    await interaction.response.send_message(f"❌ {gracz.mention} usunięty z **{club_name}**")

@bot.tree.command(name="dodaj_kase", description="Dodaj kasę klubowi (tylko admin)")
@app_commands.describe(klub="Klub", kwota="Kwota", powód="Powód")
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
    # Sprawdź uprawnienia
    allowed_roles = ["Owner", "Admin", "Zarząd"]
    if not any(role.name in allowed_roles for role in interaction.user.roles):
        await interaction.response.send_message("❌ Brak uprawnień!", ephemeral=True)
        return
    
    if klub not in CLUBS:
        await interaction.response.send_message("❌ Nieznany klub!", ephemeral=True)
        return
    
    club = CLUBS[klub]
    
    # Dodaj kasę
    conn = sqlite3.connect('clubs.db')
    c = conn.cursor()
    
    # Stare saldo
    c.execute("SELECT balance FROM clubs WHERE club_name = ?", (club['name'],))
    old_balance = c.fetchone()[0]
    
    # Nowe saldo
    c.execute("UPDATE clubs SET balance = balance + ? WHERE club_name = ?", (kwota, club['name']))
    
    c.execute("SELECT balance FROM clubs WHERE club_name = ?", (club['name'],))
    new_balance = c.fetchone()[0]
    
    # Historia
    c.execute('''INSERT INTO transactions (club_from, club_to, amount, reason, timestamp) 
                 VALUES (?, ?, ?, ?, ?)''',
                 ("SYSTEM", club['name'], kwota, powód, datetime.now()))
    
    conn.commit()
    conn.close()
    
    # Odpowiedź
    embed = discord.Embed(
        title="💸 DODANO KASĘ",
        color=discord.Color.green()
    )
    embed.add_field(name="Klub", value=club['name'])
    embed.add_field(name="Kwota", value=f"`+${kwota:,}`")
    embed.add_field(name="Nowe saldo", value=f"`${new_balance:,}`")
    embed.add_field(name="Powód", value=powód)
    embed.add_field(name="Dodał", value=interaction.user.mention)
    
    await interaction.response.send_message(embed=embed)
    
    # Aktualizuj kanały
    await update_saldo_channel(klub)
    await update_ranking_channel()

@bot.tree.command(name="aktualizuj_kanały", description="Aktualizuj kanały (tylko admin)")
async def aktualizuj_kanały(interaction: discord.Interaction):
    """Ręczna aktualizacja kanałów"""
    allowed_roles = ["Owner", "Admin", "Zarząd"]
    if not any(role.name in allowed_roles for role in interaction.user.roles):
        await interaction.response.send_message("❌ Brak uprawnień!", ephemeral=True)
        return
    
    await interaction.response.send_message("🔄 Aktualizuję kanały...")
    await update_all_channels()
    await interaction.followup.send("✅ Kanały zaktualizowane!")

# ========== URUCHOMIENIE ==========
if __name__ == "__main__":
    print("="*60)
    print("🤖 SYSTEM KLUBÓW PIŁKARSKICH")
    print("="*60)
    
    # Sprawdź token
    if not TOKEN:
        print("❌ BRAK TOKENA DISCORD!")
        print("ℹ️ Dla hostingu: Dodaj DISCORD_TOKEN w Environment Variables")
        print("ℹ️ Dla komputera: Odkomentuj TOKEN w linijce 13")
        sys.exit(1)
    
    print(f"✅ Token: {'*' * 20}")
    print(f"✅ Kluby: {len(CLUBS)}")
    print("="*60)
    
    # Uruchom bota
    try:
        bot.run(TOKEN)
    except discord.errors.LoginFailure:
        print("❌ BŁĄD LOGOWANIA: Nieprawidłowy token")
        print("ℹ️ Sprawdź token w Discord Dev Portal")
    except Exception as e:
        print(f"❌ BŁĄD: {e}")