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

# Change the data file to server_lore.json
DATA_FILE = "server_lore.json"

# Your specific Test Server ID for instant slash command syncing
TEST_GUILD_ID = discord.Object(id=1551157172589690982)

# Add any custom phrases you want your bot to skip entirely during learning
WORD_BLACKLIST = ["token", "password", "secret", "https://", "http://"]

def load_data():
    """Loads database or yields maximum-tier predictive nested tracking schema."""
    default_schema = {
        "quotes": [], 
        "lore": {}, 
        "user_chat_counts": {}, 
        "server_emojis": {},      # Tracks favorite server emojis: {"😂": 12}
        "trigrams": {},           # Multi-word predictive structural database: {"word1 word2": ["word3"]}
        "user_trigrams": {}       # High-definition per-user structure index: {"user_id": {"word1 word2": ["word3"]}}
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
    try:
        # Instantly sync to your specific test server
        bot.tree.copy_global_to(guild=TEST_GUILD_ID)
        await bot.tree.sync(guild=TEST_GUILD_ID)
        print("Slash commands synced instantly to your server!")
    except Exception as e:
        print(f"Sync error: {e}")
    if not status_rotator.is_running():
        status_rotator.start()

@tasks.loop(minutes=10)
async def status_rotator():
    """Reflects highly precise live calculated linguistic connections on status loop."""
    data = load_data()
    total_connections = sum(len(v) for v in data["trigrams"].values())
    await bot.change_presence(activity=discord.CustomActivity(name=f"🧠 Processing {total_connections} structural Trigram layers | /mimic"))

# --- HIGH-FREQUENCY CHAT ADAPTATION & INTELLIGENT REPLY ENGINE ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Process commands first so prefix commands work smoothly
    await bot.process_commands(message)
    if message.content.startswith("!"):
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

# --- 🆕 HYBRID / SLASH COMMAND ENGINE ---

@bot.hybrid_command(name="mimic", description="Generates a complex text string based on server learning.")
async def mimic(ctx: commands.Context):
    """Generates an AI response based on learned chat patterns."""
    data = load_data()
    advanced_reply = generate_complex_ai_mimic(data, user_id=ctx.author.id)
    
    if ctx.interaction:
        await ctx.reply(advanced_reply, ephemeral=True)
    else:
        await ctx.reply(advanced_reply)

@bot.hybrid_command(name="stats", description="Displays the bot's current neural matrix statistics.")
async def stats(ctx: commands.Context):
    """Displays tracking insights."""
    data = load_data()
    total_trigrams = sum(len(v) for v in data["trigrams"].values())
    total_quotes = len(data["quotes"])
    total_users = len(data["user_chat_counts"])
    
    embed = discord.Embed(title="🧠 Neural Brain Matrix Stats", color=discord.Color.blurple())
    embed.add_field(name="Trigram Connections", value=f"{total_trigrams:,}", inline=True)
    embed.add_field(name="Captured Quotes", value=f"{total_quotes:,}", inline=True)
    embed.add_field(name="Tracked Users", value=f"{total_users:,}", inline=True)
    
    if ctx.interaction:
        await ctx.reply(embed=embed, ephemeral=True)
    else:
        await ctx.reply(embed=embed)

# Run the bot
bot.run(os.getenv("TOKEN"))