import discord, sqlite3
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import asyncio
import os

TOKEN = "DISCORD_TOKEN"

FREE_SIGN_ID = 1454213320977551462
TRANSFERS_ID = 1453884602312556667
RANKING_CHANNEL_ID = 1454236491222876274

CLUBS = {
    "wislakrakow": {"name": "Wisła Kraków", "manager": "Prezes Wisły", "color": discord.Color.red(), "saldo_id": 1454212839144427754, "transfer_id": 1454214931397476534},
    "santos": {"name": "Santos", "manager": "Prezes Santos", "color": discord.Color.dark_purple(), "saldo_id": 1454212811348508732, "transfer_id": 1454215000905482331},
    "bazant": {"name": "Bażant Strzałkowo", "manager": "Prezes Bażanta", "color": discord.Color.green(), "saldo_id": 1454212880571564043, "transfer_id": 1454215083939860523},
    "asroma": {"name": "As Roma", "manager": "Prezes Roma", "color": discord.Color.dark_red(), "saldo_id": 1454212870370758793, "transfer_id": 1454215058006741085},
    "ukskolorado": {"name": "UKS Kolorado", "manager": "Prezes Kolorado", "color": discord.Color.blue(), "saldo_id": 1454212866289828030, "transfer_id": 1454215100071411945},
    "chelsea": {"name": "Chelsea", "manager": "Prezes Chelsea", "color": discord.Color.dark_blue(), "saldo_id": 1454212851052052652, "transfer_id": 1454215044610130071},
    "fcbarcelona": {"name": "Fc Barcelona", "manager": "Prezes Fc Barcelony", "color": discord.Color.dark_gold(), "saldo_id": 1454212885512192162, "transfer_id": 1454215070845239456},
    "juventus": {"name": "Juventus", "manager": "Prezes Juventusu", "color": discord.Color.from_rgb(0,0,0), "saldo_id": 1454212832160645305, "transfer_id": 1454215028478837019}
}

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

def init_db():
    conn = sqlite3.connect('clubs.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS clubs (club_name TEXT PRIMARY KEY, balance INTEGER DEFAULT 0, manager_role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS players (player_id TEXT, player_name TEXT, current_club TEXT, value INTEGER DEFAULT 1000, is_transfer_listed BOOLEAN DEFAULT 0, transfer_price INTEGER, listed_by TEXT, listed_at DATETIME)''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, club_from TEXT, club_to TEXT, amount INTEGER, reason TEXT, timestamp DATETIME, player_name TEXT)''')
    for club in CLUBS.values():
        c.execute('''INSERT OR IGNORE INTO clubs (club_name, manager_role, balance) VALUES (?, ?, ?)''', (club['name'], club['manager'], 50000))
    conn.commit()
    conn.close()

async def update_saldo_channel(club_id):
    if club_id not in CLUBS: return
    config = CLUBS[club_id]
    saldo_channel = bot.get_channel(config['saldo_id'])
    if not saldo_channel: return
    
    conn = sqlite3.connect('clubs.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM clubs WHERE club_name = ?", (config['name'],))
    balance = c.fetchone()[0]
    conn.close()
    
    try:
        async for message in saldo_channel.history(limit=10):
            if message.author == bot.user:
                await message.delete()
    except: pass
    
    embed = discord.Embed(title=f"💰 SALDO: {config['name']}", description=f"**Saldo:** `${balance:,}`", color=config['color'], timestamp=datetime.now())
    embed.add_field(name="👨‍💼 Prezes", value=f"`{config['manager']}`", inline=True)
    embed.set_footer(text="🔄 Aktualizowane automatycznie")
    await saldo_channel.send(embed=embed)

async def update_ranking_channel():
    ranking_channel = bot.get_channel(RANKING_CHANNEL_ID)
    if not ranking_channel: 
        print("❌ Nie znaleziono kanału rankingu!")
        return
    
    conn = sqlite3.connect('clubs.db')
    c = conn.cursor()
    c.execute("SELECT club_name, balance FROM clubs ORDER BY balance DESC")
    clubs = c.fetchall()
    conn.close()
    
    try:
        async for message in ranking_channel.history(limit=10):
            if message.author == bot.user:
                await message.delete()
    except: pass
    
    embed = discord.Embed(title="🏆 RANKING KLUBÓW", color=discord.Color.gold(), timestamp=datetime.now())
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣"]
    
    # FIX: Usuń duplikaty - grupowanie po nazwie klubu
    seen = set()
    unique_clubs = []
    for name, bal in clubs:
        if name not in seen:
            seen.add(name)
            unique_clubs.append((name, bal))
    
    for idx, (name, bal) in enumerate(unique_clubs[:8]):
        medal = medals[idx] if idx < len(medals) else f"{idx+1}."
        embed.add_field(name=f"{medal} {name}", value=f"**${bal:,}**", inline=False)
    
    await ranking_channel.send(embed=embed)

async def update_all_channels():
    print("🔄 Aktualizowanie kanałów...")
    for club_id in CLUBS.keys():
        await update_saldo_channel(club_id)
        await asyncio.sleep(0.5)
    await update_ranking_channel()
    print("✅ Wszystkie kanały zaktualizowane!")

@bot.event
async def on_ready():
    init_db()
    try:
        synced = await bot.tree.sync()
        print(f"✅ Bot: {bot.user}")
        print(f"✅ Zsynchrowano {len(synced)} komend")
    except Exception as e:
        print(f"❌ Błąd sync: {e}")
    await update_all_channels()

@bot.tree.command(name="sync", description="Ręczna synchronizacja komend (tylko admin)")
async def sync(interaction: discord.Interaction):
    if interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🔄 Synchronizacja komend...")
        try:
            synced = await bot.tree.sync()
            await interaction.followup.send(f"✅ Zsynchrowano {len(synced)} komend")
        except Exception as e:
            await interaction.followup.send(f"❌ Błąd: {e}")
    else:
        await interaction.response.send_message("❌ Brak uprawnień administratora!", ephemeral=True)

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
    if klub not in CLUBS: 
        await interaction.response.send_message("❌ Nieznany klub!", ephemeral=True)
        return
    
    c = CLUBS[klub]
    
    if not any(r.name == c["manager"] for r in interaction.user.roles):
        await interaction.response.send_message(f"❌ Brak roli: **{c['manager']}**", ephemeral=True)
        return
    
    conn = sqlite3.connect('clubs.db')
    cur = conn.cursor()
    cur.execute("SELECT current_club FROM players WHERE player_id = ?", (str(gracz.id),))
    if cur.fetchone():
        await interaction.response.send_message(f"❌ {gracz.mention} już w klubie", ephemeral=True)
        conn.close()
        return
    
    cur.execute('''INSERT INTO players (player_id, player_name, current_club, value) 
                   VALUES (?, ?, ?, ?)''', (str(gracz.id), gracz.display_name, c['name'], 1000))
    
    role = discord.utils.get(interaction.guild.roles, name=c['name'])
    if not role:
        role = await interaction.guild.create_role(name=c['name'], color=c['color'])
    await gracz.add_roles(role)
    
    conn.commit()
    conn.close()
    
    await interaction.response.send_message(f"✅ {gracz.mention} → {c['name']}")
    
    channel = bot.get_channel(FREE_SIGN_ID)
    if channel:
        embed = discord.Embed(title="📝 FREE SIGNING", description=f"**{c['name']}** podpisał {gracz.mention}", 
                              color=c['color'], timestamp=datetime.now())
        embed.add_field(name="Prezes", value=interaction.user.mention)
        await channel.send(embed=embed)

@bot.tree.command(name="usun", description="Usuń gracza z klubu")
@app_commands.describe(gracz="Gracz")
async def usun(interaction: discord.Interaction, gracz: discord.Member):
    user_roles = [role.name for role in gracz.roles]
    club_roles = [config['name'] for config in CLUBS.values()]
    user_club_roles = [role for role in user_roles if role in club_roles]
    
    if not user_club_roles:
        await interaction.response.send_message("❌ Gracz nie jest w klubie!", ephemeral=True)
        return
    
    club_name = user_club_roles[0]
    club_config = next((c for c in CLUBS.values() if c['name'] == club_name), None)
    
    if not club_config:
        await interaction.response.send_message("❌ Błąd: klub nie znaleziony", ephemeral=True)
        return
    
    if not any(r.name == club_config['manager'] for r in interaction.user.roles):
        await interaction.response.send_message(f"❌ Nie jesteś prezesem {club_name}!", ephemeral=True)
        return
    
    try:
        role = discord.utils.get(interaction.guild.roles, name=club_name)
        if role and role in gracz.roles:
            await gracz.remove_roles(role)
    except: pass
    
    conn = sqlite3.connect('clubs.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM players WHERE player_id = ?", (str(gracz.id),))
    conn.commit()
    conn.close()
    
    await interaction.response.send_message(f"❌ {gracz.mention} usunięty z **{club_name}**")

@bot.tree.command(name="wystaw", description="Wystaw gracza na transfer")
@app_commands.describe(gracz="Gracz", cena="Cena transferu")
async def wystaw(interaction: discord.Interaction, gracz: discord.Member, cena: int):
    user_roles = [role.name for role in gracz.roles]
    club_roles = [config['name'] for config in CLUBS.values()]
    user_club_roles = [role for role in user_roles if role in club_roles]
    
    if not user_club_roles:
        await interaction.response.send_message("❌ Gracz nie jest w klubie! Najpierw `/dodaj`", ephemeral=True)
        return
    
    club_name = user_club_roles[0]
    club_config = next((c for c in CLUBS.values() if c['name'] == club_name), None)
    
    if not club_config:
        await interaction.response.send_message("❌ Błąd: klub nie znaleziony", ephemeral=True)
        return
    
    if not any(r.name == club_config['manager'] for r in interaction.user.roles):
        await interaction.response.send_message(f"❌ Nie jesteś prezesem {club_name}!", ephemeral=True)
        return
    
    conn = sqlite3.connect('clubs.db')
    cur = conn.cursor()
    
    cur.execute("SELECT current_club FROM players WHERE player_id = ?", (str(gracz.id),))
    if not cur.fetchone():
        cur.execute('''INSERT INTO players (player_id, player_name, current_club, value) 
                       VALUES (?, ?, ?, ?)''', (str(gracz.id), gracz.display_name, club_name, 1000))
    
    cur.execute('''UPDATE players SET is_transfer_listed = 1, transfer_price = ?, 
                   listed_by = ?, listed_at = ? WHERE player_id = ?''', 
                   (cena, interaction.user.name, datetime.now(), str(gracz.id)))
    
    conn.commit()
    conn.close()
    
    await interaction.response.send_message(f"✅ {gracz.mention} wystawiony za **${cena:,}**\nID: `{gracz.id}`")
    
    transfer_channel = bot.get_channel(club_config['transfer_id'])
    if transfer_channel:
        embed = discord.Embed(title="📋 GRACZ NA TRANSFER", color=club_config['color'], timestamp=datetime.now())
        embed.add_field(name="Gracz", value=gracz.mention, inline=True)
        embed.add_field(name="Klub", value=club_name, inline=True)
        embed.add_field(name="Cena", value=f"**${cena:,}**", inline=True)
        embed.add_field(name="ID Gracza", value=f"`{gracz.id}`", inline=True)
        embed.set_footer(text=f"Kup komendą: /kup {gracz.id}")
        await transfer_channel.send(embed=embed)

@bot.tree.command(name="kup", description="Kup gracza z listy transferowej")
@app_commands.describe(gracz_id="ID gracza (znajdz na kanale transferowym)")
async def kup(interaction: discord.Interaction, gracz_id: str):
    conn = sqlite3.connect('clubs.db')
    cur = conn.cursor()
    
    cur.execute('''SELECT player_name, current_club, transfer_price, listed_by 
                   FROM players WHERE player_id = ? AND is_transfer_listed = 1''', (gracz_id,))
    player = cur.fetchone()
    
    if not player:
        await interaction.response.send_message("❌ Gracz nie jest na liście transferowej!", ephemeral=True)
        conn.close()
        return
    
    player_name, seller_club, price, listed_by = player
    
    cur.execute("SELECT balance FROM clubs WHERE club_name = ?", (seller_club,))
    seller_balance = cur.fetchone()[0]
    
    buyer_config = None
    buyer_club_name = None
    for config in CLUBS.values():
        if any(r.name == config['manager'] for r in interaction.user.roles):
            buyer_config = config
            buyer_club_name = config['name']
            break
    
    if not buyer_config:
        await interaction.response.send_message("❌ Nie jesteś prezesem żadnego klubu!", ephemeral=True)
        conn.close()
        return
    
    if buyer_club_name == seller_club:
        await interaction.response.send_message("❌ Nie możesz kupić gracza z własnego klubu!", ephemeral=True)
        conn.close()
        return
    
    cur.execute("SELECT balance FROM clubs WHERE club_name = ?", (buyer_club_name,))
    buyer_balance = cur.fetchone()[0]
    
    if buyer_balance < price:
        await interaction.response.send_message(f"❌ Masz tylko ${buyer_balance:,}, potrzebujesz ${price:,}!", ephemeral=True)
        conn.close()
        return
    
    cur.execute("UPDATE clubs SET balance = balance + ? WHERE club_name = ?", (price, seller_club))
    cur.execute("UPDATE clubs SET balance = balance - ? WHERE club_name = ?", (price, buyer_club_name))
    
    cur.execute('''UPDATE players SET current_club = ?, is_transfer_listed = 0, 
                   transfer_price = NULL, listed_by = NULL, listed_at = NULL 
                   WHERE player_id = ?''', (buyer_club_name, gracz_id))
    
    cur.execute('''INSERT INTO transactions (club_from, club_to, amount, reason, timestamp, player_name) 
                   VALUES (?, ?, ?, ?, ?, ?)''', 
                   (buyer_club_name, seller_club, price, f"Transfer: {player_name}", datetime.now(), player_name))
    
    conn.commit()
    conn.close()
    
    guild = interaction.guild
    seller_role = discord.utils.get(guild.roles, name=seller_club)
    buyer_role = discord.utils.get(guild.roles, name=buyer_club_name)
    
    gracz_member = guild.get_member(int(gracz_id))
    if gracz_member:
        if seller_role and seller_role in gracz_member.roles:
            await gracz_member.remove_roles(seller_role)
        if buyer_role:
            await gracz_member.add_roles(buyer_role)
    
    await interaction.response.send_message(f"✅ {player_name} kupiony przez {buyer_club_name} za **${price:,}**")
    
    for club_id, config in CLUBS.items():
        if config['name'] == seller_club or config['name'] == buyer_club_name:
            await update_saldo_channel(club_id)
    
    await update_ranking_channel()

@bot.tree.command(name="lista_transferowa", description="Pokaż listę transferową")
async def lista_transferowa(interaction: discord.Interaction):
    conn = sqlite3.connect('clubs.db')
    cur = conn.cursor()
    cur.execute('''SELECT player_name, current_club, transfer_price, listed_by, listed_at 
                   FROM players WHERE is_transfer_listed = 1 ORDER BY listed_at DESC''')
    players = cur.fetchall()
    conn.close()
    
    if not players:
        await interaction.response.send_message("ℹ️ Brak graczy na liście transferowej", ephemeral=True)
        return
    
    embed = discord.Embed(title="📋 LISTA TRANSFEROWA", color=discord.Color.blue(), timestamp=datetime.now())
    embed.set_footer(text=f"Kup komendą: /kup <ID_GRACZA>")
    
    for player_name, club, price, listed_by, listed_at in players[:10]:
        embed.add_field(
            name=f"🏷️ {player_name}",
            value=f"**Klub:** {club}\n**Cena:** ${price:,}\n**Wystawił:** {listed_by}\n**Data:** {listed_at[:16] if listed_at else 'Brak'}",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="historia", description="Pokaż historię transakcji klubu")
@app_commands.describe(limit="Ilość transakcji do wyświetlenia (max 20)")
async def historia(interaction: discord.Interaction, limit: int = 10):
    if limit > 20:
        limit = 20
    
    user_club = None
    for config in CLUBS.values():
        if any(r.name == config['manager'] for r in interaction.user.roles):
            user_club = config['name']
            break
    
    if not user_club:
        await interaction.response.send_message("❌ Nie jesteś prezesem żadnego klubu!", ephemeral=True)
        return
    
    conn = sqlite3.connect('clubs.db')
    cur = conn.cursor()
    cur.execute('''SELECT club_from, club_to, amount, reason, timestamp, player_name 
                   FROM transactions 
                   WHERE club_from = ? OR club_to = ? 
                   ORDER BY timestamp DESC LIMIT ?''', (user_club, user_club, limit))
    transactions = cur.fetchall()
    conn.close()
    
    if not transactions:
        await interaction.response.send_message(f"ℹ️ Brak transakcji dla {user_club}", ephemeral=True)
        return
    
    embed = discord.Embed(title=f"📜 HISTORIA: {user_club}", color=discord.Color.green(), timestamp=datetime.now())
    
    for club_from, club_to, amount, reason, timestamp, player_name in transactions:
        if club_from == "SYSTEM":
            description = f"💰 **+${amount:,}** - {reason}"
        elif club_to == user_club:
            description = f"🟢 **+${amount:,}** od {club_from}\n{reason}"
        else:
            description = f"🔴 **-${amount:,}** do {club_to}\n{reason}"
        
        if player_name:
            description += f"\n👤 {player_name}"
        
        embed.add_field(
            name=f"🕒 {timestamp[:16] if timestamp else 'Brak daty'}",
            value=description,
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ranking", description="Pokaż ranking klubów")
async def ranking(interaction: discord.Interaction):
    conn = sqlite3.connect('clubs.db')
    cur = conn.cursor()
    cur.execute("SELECT club_name, balance FROM clubs ORDER BY balance DESC")
    clubs = cur.fetchall()
    conn.close()
    
    embed = discord.Embed(title="🏆 RANKING KLUBÓW", color=discord.Color.gold(), timestamp=datetime.now())
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣"]
    
    # FIX: Usuń duplikaty
    seen = set()
    unique_clubs = []
    for name, bal in clubs:
        if name not in seen:
            seen.add(name)
            unique_clubs.append((name, bal))
    
    for idx, (name, bal) in enumerate(unique_clubs[:8]):
        medal = medals[idx] if idx < len(medals) else f"{idx+1}."
        embed.add_field(name=f"{medal} {name}", value=f"**${bal:,}**", inline=False)
    
    if len(unique_clubs) > 8:
        other_clubs = unique_clubs[8:]
        other_text = "\n".join([f"{idx+9}. {name}: ${bal:,}" for idx, (name, bal) in enumerate(other_clubs)])
        embed.add_field(name="Pozostałe", value=other_text, inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="aktualizuj_kanały", description="Aktualizuj wszystkie kanały (tylko admin)")
async def aktualizuj_kanały(interaction: discord.Interaction):
    if not any(r.name in ["Owner","Admin","Zarząd"] for r in interaction.user.roles):
        await interaction.response.send_message("❌ Brak uprawnień!", ephemeral=True)
        return
    
    await interaction.response.send_message("🔄 Aktualizuję kanały...")
    await update_all_channels()
    await interaction.followup.send("✅ Wszystkie kanały zaktualizowane!")

@bot.tree.command(name="dodaj_kase", description="Dodaj kasę klubowi")
@app_commands.describe(klub="Klub", kwota="Kwota", powód="Powód (np. wygrany mecz)")
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
    if not any(r.name in ["Owner","Admin","Zarząd"] for r in interaction.user.roles):
        await interaction.response.send_message("❌ Brak uprawnień!", ephemeral=True)
        return
    
    conn = sqlite3.connect('clubs.db')
    cur = conn.cursor()
    
    cur.execute("UPDATE clubs SET balance = balance + ? WHERE club_name = ?", 
                (kwota, CLUBS[klub]['name']))
    
    cur.execute('''INSERT INTO transactions (club_from, club_to, amount, reason, timestamp) 
                   VALUES (?, ?, ?, ?, ?)''', 
                   ("SYSTEM", CLUBS[klub]['name'], kwota, powód, datetime.now()))
    
    cur.execute("SELECT balance FROM clubs WHERE club_name = ?", (CLUBS[klub]['name'],))
    new_balance = cur.fetchone()[0]
    
    conn.commit()
    conn.close()
    
    embed = discord.Embed(title="💸 DODANO KASĘ", color=discord.Color.green())
    embed.add_field(name="Klub", value=CLUBS[klub]['name'])
    embed.add_field(name="Kwota", value=f"${kwota:,}")
    embed.add_field(name="Nowe saldo", value=f"${new_balance:,}")
    embed.add_field(name="Dodał", value=interaction.user.mention)
    
    await interaction.response.send_message(embed=embed)
    
    await update_saldo_channel(klub)
    await update_ranking_channel()

if __name__ == "__main__":
    print("="*60)
    print("🤖 SYSTEM KLUBOWY - NAPRAWIONA BARCELONA")
    print("✅ Tylko jedna Barcelona: 'Fc Barcelona'")
    print("✅ Naprawione duplikaty w rankingu")
    print("="*60)
    
    # Uruchom bota
    if TOKEN.startswith("MTQ1NDE0OTM4NDI5MDgzMjQ5NA"):
        print("🚀 Uruchamianie bota z podanym tokenem...")
        bot.run(TOKEN)
    else:
        print("❌ Token nieprawidłowy. Sprawdź czy token zaczyna się od 'MTQ1NDE0OTM4NDI5MDgzMjQ5NA'")