import os
import json
import random
import asyncio
import re
from datetime import datetime
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()

# Setup maximum explicit gateway privileges
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True  
intents.members = True 

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
DATA_FILE = "advanced_brain_matrix.json"

# Add any custom phrases you want your bot to skip entirely during learning
WORD_BLACKLIST = ["token", "password", "secret", "https://", "http://"]

def load_data():
    """Loads database or yields maximum-tier predictive nested tracking schema."""
    default_schema = {
        "quotes": [], 
        "lore": {}, 
        "user_chat_counts": {}, 
        "server_emojis": {},       # Tracks favorite server emojis: {"😂": 12}
        "trigrams": {},            # Multi-word predictive structural database: {"word1 word2": ["word3"]}
        "user_trigrams": {}        # High-definition per-user structure index: {"user_id": {"word1 word2": ["word3"]}}
    }
    if not os.path.exists(DATA_FILE):
        return default_schema
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure complex sub-dictionaries exist
            for key in default_schema:
                if key not in data:
                    data[key] = default_schema[key]
            return data
    except json.JSONDecodeError:
        return default_schema

def save_data(data):
    """Safely and securely commits massive memory matrix state changes to disk."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def clean_token(token):
    """Deep structural text cleaning to isolate pure linguistic mechanics."""
    if any(blacklisted in token for blacklisted in WORD_BLACKLIST):
        return ""
    return token.strip(".,!?\"()[]{}*<>~`").lower()

def learn_sentence_trigrams(data, text, user_id=None):
    """Breaks down text strings into complex overlapping word clusters for structural mimicry."""
    raw_tokens = text.split()
    tokens = [clean_token(t) for t in raw_tokens if clean_token(t)]
    
    # Trace standard individual emojis used inside the server text layout
    emojis = re.findall(r'<a?:[a-zA-Z0-9_]+:[0-9]+>|[\u2600-\u27BF]|[\U0001f300-\U0001f64f]|[\U0001f680-\U0001f6ff]', text)
    for emo in emojis:
        data["server_emojis"][emo] = data["server_emojis"].get(emo, 0) + 1

    if len(tokens) < 3:
        if len(tokens) == 2:
            key = f"__start__ {tokens[0]}"
            _append_trigram(data, key, tokens[1], user_id)
        return

    user_id = str(user_id) if user_id else None

    # Track starting sequence paths
    _append_trigram(data, "__start__ __start__", tokens[0], user_id)
    _append_trigram(data, f"__start__ {tokens[0]}", tokens[1], user_id)

    # Map out complex sentence patterns three items at a time
    for i in range(len(tokens) - 2):
        w1, w2, w3 = tokens[i], tokens[i+1], tokens[i+2]
        key = f"{w1} {w2}"
        _append_trigram(data, key, w3, user_id)

def _append_trigram(data, key, value, user_id=None):
    """Internal micro-helper to map data matrix branches safely."""
    if key not in data["trigrams"]:
        data["trigrams"][key] = []
    data["trigrams"][key].append(value)
    
    if user_id:
        if user_id not in data["user_trigrams"]:
            data["user_trigrams"][user_id] = {}
        if key not in data["user_trigrams"][user_id]:
            data["user_trigrams"][user_id][key] = []
        data["user_trigrams"][user_id][key].append(value)

def generate_complex_ai_mimic(data, user_id=None, seed_word=None, max_words=20):
    """Assembles complex, contextually linked text strings using predictive algorithms."""
    pool = data["trigrams"]
    if user_id and str(user_id) in data["user_trigrams"]:
        pool = data["user_trigrams"][str(user_id)]

    if not pool:
        return "tbh fr fr lol"

    w1, w2 = "__start__", "__start__"
    
    if seed_word and seed_word.lower() in pool:
        match_keys = [k for k in pool.keys() if k.startswith(seed_word.lower())]
        if match_keys:
            w1, w2 = random.choice(match_keys).split()

    sentence = []
    if w1 != "__start__": sentence.append(w1)
    if w2 != "__start__": sentence.append(w2)

    for _ in range(max_words):
        key = f"{w1} {w2}"
        if key in pool and pool[key]:
            next_word = random.choice(pool[key])
            sentence.append(next_word)
            w1, w2 = w2, next_word
        else:
            fallback_keys = [k for k in pool.keys() if k.startswith(w2)]
            if fallback_keys:
                fallback_key = random.choice(fallback_keys)
                parts = fallback_key.split()
                w1 = parts[0] if len(parts) > 0 else "__start__"
                w2 = parts[1] if len(parts) > 1 else "__start__"
            else:
                if sentence and random.random() < 0.4:
                    break
                random_key = random.choice(list(pool.keys()))
                parts = random_key.split()
                w1 = parts[0] if len(parts) > 0 else "__start__"
                w2 = parts[1] if len(parts) > 1 else "__start__"
                if w1 != "__start__": 
                    sentence.append(w1)

    if not sentence:
        return "idk fr lol"

    flavor_elements = [" lol", " fr", " fr fr", " lmao", " smh", " fr matching the energy", "", "!?"]
    if data.get("server_emojis"):
        top_emoji = max(data["server_emojis"], key=data["server_emojis"].get)
        if random.random() < 0.3:
            flavor_elements.append(f" {top_emoji}")

    return " ".join(sentence).capitalize() + random.choice(flavor_elements)

@bot.event
async def on_ready():
    print(f"👑 MAX-POWER V4.0 AI LORE CLONE ONLINE: {bot.user.name} (ID: {bot.user.id})")
    if not status_rotator.is_running():
        status_rotator.start()

@tasks.loop(minutes=10)
async def status_rotator():
    """Reflects highly precise live calculated linguistic connections on status loop."""
    data = load_data()
    total_connections = sum(len(v) for v in data["trigrams"].values())
    await bot.change_presence(activity=discord.CustomActivity(name=f"🧠 Processing {total_connections} structural Trigram layers | !help"))

# --- HIGH-FREQUENCY CHAT ADAPTATION & INTELLIGENT REPLY ENGINE ---
@bot.event
async def on_message(message):
    if message.author.bot or message.content.startswith("!"):
        await bot.process_commands(message)
        return

    data = load_data()
    user_id = str(message.author.id)
    
    # 1. Update activity matrix indexes
    data["user_chat_counts"][user_id] = data["user_chat_counts"].get(user_id, 0) + 1
    
    # 2. Extract syntactic structural insights live
    learn_sentence_trigrams(data, message.content, user_id)
    
    # 3. Autonomous High-Quality Auto-Quote capturing
    if len(message.content) > 25 and random.random() < 0.02:
        if not any(q['text'] == message.content for q in data["quotes"]):
            data["quotes"].append({
                "text": message.content,
                "added_by": f"{message.author.display_name} (Calculated Lore Capture 🤖)",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            await message.add_reaction("👑") 

    save_data(data)
    
    # 4. 🧠 CONTEXTUAL AUTO-REPLY GENERATOR (4% baseline trigger chance)
    if random.random() < 0.04 and len(data["trigrams"]) > 25:
        async with message.channel.typing():
            await asyncio.sleep(random.uniform(0.6, 1.8))
            
            potential_seeds = [w for w in message.content.split() if len(w) > 3]
            seed = random.choice(potential_seeds) if potential_seeds else None
            
            target = random.choice([None, user_id])
            advanced_reply = generate_complex_ai_mimic(data, user_id=target, seed_word=seed)
            await message.channel.send(advanced_reply)

    await bot.process_commands(message)

# --- 🚀 MAXIMUM SCALE ULTRA-SWEEP SERVER BRAINSCANNER (20,000 MESSAGE DEPTH) ---
@bot.command(name="brainscan")
@commands.has_permissions(administrator=True)
async def maximum_power_scan(ctx):
    """Deep indexes up to 20,000 recent messages across all accessible server pipelines."""
    status_msg = await ctx.send("💥 **DEEP MATRIX CORE HARVEST INITIATED...** Interfacing with high-capacity historical server chat indexes...")
    
    data = load_data()
    total_scanned = 0
    
    target_channels = [ctx.channel] + [c for c in ctx.guild.text_channels if c != ctx.channel and c.permissions_for(ctx.guild.me).read_message_history][:7]
    
    for channel in target_channels:
        try:
            async for message in channel.history(limit=2500):
                if message.author.bot or message.content.startswith("!"):
                    continue
                    
                total_scanned += 1
                u_id = str(message.author.id)
                data["user_chat_counts"][u_id] = data["user_chat_counts"].get(u_id, 0) + 1
                
                learn_sentence_trigrams(data, message.content, u_id)
                if total_scanned >= 20000:
                    break
        except Exception as e:
            print(f"Skipping server layout lane {channel.name}: {e}")
            continue
            
        if total_scanned >= 20000:
            break
            
    save_data(data)
    total_connections = sum(len(v) for v in data["trigrams"].values())
    await status_msg.edit(content=f"👑 **Ultra-Deep Ingestion Vector Complete!** Scanned `{total_scanned}` historic messages. Built `{total_connections}` multi-word Trigram syntax pathways. Let the matrix rule.")

# --- DYNAMIC ADAPTIVE IMITATION SYSTEM ---
@bot.command(name="mimic")
async def execute_advanced_mimic(ctx, member: discord.Member = None):
    """Simulates targeted server clone syntax patterns. Usage: !mimic or !mimic @User"""
    data = load_data()
    potential_seeds = [w for w in ctx.message.content.split() if not w.startswith("!") and not w.startswith("<@")]
    seed = random.choice(potential_seeds) if potential_seeds else None
    
    if member:
        user_id = str(member.id)
        if user_id not in data["user_trigrams"] or len(data["user_trigrams"][user_id]) < 10:
            return await ctx.send(f"❌ My localized prediction matrix on {member.display_name} is insufficient. Provide more history variables via text or run !brainscan!")
        simulated_text = generate_complex_ai_mimic(data, user_id=user_id, seed_word=seed)
        await ctx.send(f"👤 Simulated Clone Matrix ({member.display_name}): \"{simulated_text}\"")
    else:
        if len(data["trigrams"]) < 15:
            return await ctx.send("📭 Structural Trigram density is too low inside current matrix files. Run !brainscan!")
        simulated_text = generate_complex_ai_mimic(data, seed_word=seed)
        await ctx.send(f"👥 Simulated Hive Collective: \"{simulated_text}\"")

# --- QUANTUM STATS DISPLAY INFRASTRUCTURE ---
@bot.command(name="brainstats")
async def display_quantum_stats(ctx):
    """Displays comprehensive analytical diagnostic breakdown elements of language processing modules."""
    data = load_data()
    total_paths = sum(len(v) for v in data["trigrams"].values())
    embed = discord.Embed(
        title="🛰️ Core Simulation Processing Metrics",
        description="Linguistic structural parameters computed natively by the underlying model.",
        color=discord.Color.dark_green()
    )
    embed.add_field(name="🔗 Trigram Matrix Links", value=f"{total_paths} data weights", inline=True)
    embed.add_field(name="🔤 Unique Structural Nodes", value=f"{len(data['trigrams'])} configurations", inline=True)
    if data.get("server_emojis"):
        top_emoji = max(data["server_emojis"], key=data["server_emojis"].get)
        embed.add_field(name="🎭 Favorite Aesthetic Anchor", value=f"{top_emoji} ({data['server_emojis'][top_emoji]} uses)", inline=True)
    counts = data.get("user_chat_counts", {})
    if counts:
        sorted_chatter = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:3]
        leaderboard = []
        for rank, (u_id, amt) in enumerate(sorted_chatter, 1):
            m = ctx.guild.get_member(int(u_id))
            m_name = m.display_name if m else f"User ID {u_id}"
            leaderboard.append(f"{rank}. {m_name} — {amt} syntax points collected")
        embed.add_field(name="📊 High-Yield Persona Profiles", value="\n".join(leaderboard), inline=False)
    await ctx.send(embed=embed)

# --- 100% REBUILT HIGH-IMPACT COMMAND GUIDE ---
@bot.command(name="help")
async def render_max_power_help(ctx):
    embed = discord.Embed(
        title="🛰️ Server LoreBot v4.0 - Custom AI Trigram Engine",
        description="An advanced structural text engine running deep contextual processing hooks to perfectly simulate your friend group.",
        color=discord.Color.purple()
    )
    embed.add_field(
        name="🔮 Max-Power Simulation Commands",
        value=(
            "!brainscan - Concurrently scrapes up to 20,000 chat lines across 7 core channels (Admin Only)\n"
            "!mimic - Generates a blended predictive server statement string\n"
            "!mimic @User - Isolates vectors to perfectly impersonate one specific friend\n"
            "!brainstats - Evaluates current algorithm links and lists most mapped text profiles"
        ),
        inline=False
    )
    embed.add_field(
        name="💬 Classic Systems Included",
        value=(
            "!quote <text> / !randomquote / !listquotes - Elite archive commands\n"
            "!define / !lookup / !listlore - Server inside joke wiki lookup commands\n"
            "!searchmsg <word> - Safe textual channel message analysis checker\n"
            "🔖 Active Hook: Reacting to any message with a bookmark icon auto-saves it safely!"
        ),
        inline=False
    )
    embed.set_footer(text="Linguistic framework engine actively monitoring all incoming text streams.")
    await ctx.send(embed=embed)

# --- THE BOTTOM WRAP OF LORE MODULE CODES ---
class QuoteView(discord.ui.View):
    def __init__(self): 
        super().__init__(timeout=180)
        
    @discord.ui.button(label="Roll Another Quote", style=discord.ButtonStyle.blurple, emoji="🔄")
    async def roll_again(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        quotes = data.get("quotes", [])
        if not quotes: 
            return await interaction.response.send_message("📭 Archive empty!", ephemeral=True)
        chosen = random.choice(quotes)
        embed = discord.Embed(description=f"💬 \"{chosen['text']}\"", color=discord.Color.gold())
        embed.set_footer(text=f"Added by {chosen['added_by']} • {chosen['timestamp']}")
        await interaction.response.edit_message(embed=embed, view=self)

@bot.command(name="quote")
async def add_quote(ctx, *, quote_text: str = None):
    if not quote_text: 
        return await ctx.send("❌ Usage: !quote <text>")
    data = load_data()
    data["quotes"].append({"text": quote_text, "added_by": ctx.author.display_name, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")})
    save_data(data)
    embed = discord.Embed(title="📥 Quote Archived", description=f"\"{quote_text}\"", color=discord.Color.green())
    await ctx.send(embed=embed)

@bot.command(name="randomquote")
async def random_quote(ctx):
    data = load_data()
    quotes = data.get("quotes", [])
    if not quotes: 
        return await ctx.send("📭 Archive empty!")
    chosen = random.choice(quotes)
    embed = discord.Embed(description=f"💬 \"{chosen['text']}\"", color=discord.Color.gold())
    embed.set_footer(text=f"Added by {chosen['added_by']} • {chosen['timestamp']}")
    await ctx.send(embed=embed, view=QuoteView())

@bot.command(name="listquotes")
async def list_quotes(ctx):
    data = load_data()
    quotes = data.get("quotes", [])
    if not quotes: 
        return await ctx.send("📭 No quotes saved yet!")
    lines = [f"{i}. \"{q['text'][:40]}...\" — {q['added_by']}" for i, q in enumerate(quotes[-10:], 1)]
    await ctx.send(embed=discord.Embed(title="💬 Quote Archive", description="\n".join(lines), color=discord.Color.gold()))

@bot.command(name="define")
async def define_lore(ctx, term: str = None, *, explanation: str = None):
    if not term or not explanation: 
        return await ctx.send("❌ Use !define <term> <explanation>")
    data = load_data()
    data["lore"][term.lower()] = {"original_term": term, "explanation": explanation, "defined_by": ctx.author.display_name}
    save_data(data)
    await ctx.send(f"📚 Lore documented for '{term}'!")

@bot.command(name="lookup")
async def lookup_lore(ctx, *, term: str = None):
    if not term: 
        return await ctx.send("❌ Specify what term to lookup.")
    data = load_data()
    item = data["lore"].get(term.lower())
    if not item:
        all_terms = [i["original_term"] for i in data["lore"].values()]
        suggestions = [t for t in all_terms if term.lower() in t.lower()]
        msg = f"🔍 No lore entry found for '{term}'."
        if suggestions: 
            msg += f"\n\nDid you mean: {', '.join([f'{s}' for s in suggestions[:3]])}?"
        return await ctx.send(msg)
    embed = discord.Embed(title=f"📜 {item['original_term']}", description=item["explanation"], color=discord.Color.blue())
    await ctx.send(embed=embed)

@bot.command(name="listlore")
async def list_lore(ctx):
    data = load_data()
    lore = data.get("lore", {})
    if not lore: 
        return await ctx.send("📚 No lore terms documented yet!")
    terms = [item['original_term'] for item in lore.values()]
    await ctx.send(embed=discord.Embed(title="📚 Inside Jokes", description=", ".join(terms), color=discord.Color.blue()))

@bot.command(name="searchmsg")
async def search_messages(ctx, *, keyword: str = None):
    if not keyword: 
        return await ctx.send("❌ Provide a word to scan.")
    searching_msg = await ctx.send(f"🔍 Scanning history for '{keyword}'...")
    found_messages = []
    try:
        async for message in ctx.channel.history(limit=100):
            if message.author.bot or message.content.startswith("!"): 
                continue
            if keyword.lower() in message.content.lower(): 
                found_messages.append(message)
        await searching_msg.delete()
        if not found_messages: 
            return await ctx.send(f"❌ No matching messages.")
        newest = found_messages[0]
        embed = discord.Embed(title="🔍 Keyword Match", description=f"\"{newest.content}\"", color=discord.Color.purple())
        embed.set_footer(text=f"Sent by {newest.author.display_name}")
        await ctx.send(embed=embed)
    except Exception as e: 
        print(f"Error in searchmsg: {e}")

@bot.event
async def on_raw_reaction_add(payload):
    if str(payload.emoji) == "🔖":
        channel = bot.get_channel(payload.channel_id)
        if not channel: 
            return
        try:
            message = await channel.fetch_message(payload.message_id)
            if message.author.bot or not message.content: 
                return
            guild = bot.get_guild(payload.guild_id)
            reactor = await guild.fetch_member(payload.user_id) if guild else None
            data = load_data()
            if any(q['text'] == message.content for q in data["quotes"]): 
                return
            data["quotes"].append({
                "text": message.content, 
                "added_by": f"{message.author.display_name} (via 🔖 by {reactor.display_name if reactor else 'Someone'})", 
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            save_data(data)
            await channel.send(embed=discord.Embed(title="🔖 Story Bookmarked!", description=f"\"{message.content}\"\n\n— Saved to archive.", color=discord.Color.green()))
        except Exception as e: 
            print(f"Failed to bookmark reaction: {e}")

bot.run(os.getenv("DISCORD_TOKEN"))