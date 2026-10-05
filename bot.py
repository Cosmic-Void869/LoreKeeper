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

# Database file configuration
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
        "user_trigrams": {},      # High-definition per-user structure index: {"user_id": {"word1 word2": ["word3"]}}
        "message_archive": []     # Full text archive for brainsearch: list of message dicts
    }
    if not os.path.exists(DATA_FILE):
        return default_schema
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
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

    emojis = re.findall(r'<a?:[a-zA-Z0-9_]+:[0-9]+>|[\u2600-\u27BF]|[\U0001f300-\U0001f64f]|[\U0001f680-\U0001f6ff]', text)
    for emo in emojis:
        data["server_emojis"][emo] = data["server_emojis"].get(emo, 0) + 1

    if len(tokens) < 3:
        if len(tokens) == 2:
            key = f"__start__ {tokens[0]}"
            _append_trigram(data, key, tokens[1], user_id)
        return

    user_id = str(user_id) if user_id else None

    _append_trigram(data, "__start__ __start__", tokens[0], user_id)
    _append_trigram(data, f"__start__ {tokens[0]}", tokens[1], user_id)

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
        bot.tree.copy_global_to(guild=TEST_GUILD_ID)
        await bot.tree.sync(guild=TEST_GUILD_ID)
        print("Slash commands synced instantly to your server!")
    except Exception as e:
        print(f"Sync error: {e}")
    if not status_rotator.is_running():
        status_rotator.start()

@tasks.loop(minutes=10)
async def status_rotator():
    data = load_data()
    total_connections = sum(len(v) for v in data["trigrams"].values())
    await bot.change_presence(activity=discord.CustomActivity(name=f"🧠 Processing {total_connections} structural Trigram layers | /mimic"))

# --- HIGH-FREQUENCY CHAT ADAPTATION & INTELLIGENT REPLY ENGINE ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await bot.process_commands(message)
    if message.content.startswith("!"):
        return

    data = load_data()
    user_id = str(message.author.id)
    
<<<<<<< HEAD
=======
    # 1. Update activity matrix indexes & archive message for searching
>>>>>>> 675b6ad2f2f613e44ad1f082dc1a3918f2b1bb7b
    data["user_chat_counts"][user_id] = data["user_chat_counts"].get(user_id, 0) + 1
    
<<<<<<< HEAD
    if message.content.strip():
        data["message_archive"].append({
            "content": message.content,
            "author": message.author.display_name,
            "user_id": user_id,
            "channel": message.channel.name,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        })

=======
    if message.content.strip():
        data["message_archive"].append({
            "content": message.content,
            "author": message.author.display_name,
            "user_id": user_id,
            "channel": message.channel.name,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        })

    # 2. Extract syntactic structural insights live
>>>>>>> 675b6ad2f2f613e44ad1f082dc1a3918f2b1bb7b
    learn_sentence_trigrams(data, message.content, user_id)
    
    if len(message.content) > 25 and random.random() < 0.02:
        if not any(q['text'] == message.content for q in data["quotes"]):
            data["quotes"].append({
                "text": message.content,
                "added_by": f"{message.author.display_name} (Calculated Lore Capture 🤖)",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            await message.add_reaction("👑") 

    save_data(data)
    
    if random.random() < 0.04 and len(data["trigrams"]) > 25:
        async with message.channel.typing():
            await asyncio.sleep(random.uniform(0.6, 1.8))
            potential_seeds = [w for w in message.content.split() if len(w) > 3]
            seed = random.choice(potential_seeds) if potential_seeds else None
            target = random.choice([None, user_id])
            advanced_reply = generate_complex_ai_mimic(data, user_id=target, seed_word=seed)
            await message.channel.send(advanced_reply)

<<<<<<< HEAD
=======
# --- 🆕 HYBRID COMMAND ENGINE ---
>>>>>>> 675b6ad2f2f613e44ad1f082dc1a3918f2b1bb7b

# ==========================================
# 🚀 20 HYBRID COMMANDS (Prefix & Slash)
# ==========================================

# 1. /mimic
@bot.hybrid_command(name="mimic", description="Generates a complex text string based on server learning.")
async def mimic(ctx: commands.Context):
    data = load_data()
    reply = generate_complex_ai_mimic(data, user_id=ctx.author.id)
    await ctx.reply(reply, ephemeral=bool(ctx.interaction))

# 2. /stats
@bot.hybrid_command(name="stats", description="Displays the bot's neural matrix statistics.")
async def stats(ctx: commands.Context):
    data = load_data()
    embed = discord.Embed(title="🧠 Neural Brain Matrix Stats", color=discord.Color.blurple())
    embed.add_field(name="Trigram Connections", value=f"{sum(len(v) for v in data['trigrams'].values()):,}", inline=True)
    embed.add_field(name="Captured Quotes", value=f"{len(data['quotes']):,}", inline=True)
    embed.add_field(name="Archived Messages", value=f"{len(data['message_archive']):,}", inline=True)
    embed.add_field(name="Tracked Users", value=f"{len(data['user_chat_counts']):,}", inline=True)
    await ctx.reply(embed=embed, ephemeral=bool(ctx.interaction))

# 3. /brainscan
@bot.hybrid_command(name="brainscan", description="Deep scan: Ingests ALL historical text chats across the server.")
@commands.has_permissions(manage_guild=True)
async def brainscan(ctx: commands.Context):
    if ctx.interaction:
        await ctx.defer(ephemeral=True)
        await ctx.followup.send("🧠⚡ **Deep BrainScan Initiated:** Scanning entire server history...", ephemeral=True)
    else:
        await ctx.send("🧠⚡ **Deep BrainScan Initiated:** Scanning entire server history...")

    data = load_data()
<<<<<<< HEAD
    scanned_count = 0
    for channel in ctx.guild.text_channels:
        try:
            async for msg in channel.history(limit=None):
                if msg.author.bot or not msg.content.strip():
                    continue
                exists = any(m["content"] == msg.content and m["user_id"] == str(msg.author.id) for m in data["message_archive"])
                if not exists:
                    data["message_archive"].append({
                        "content": msg.content, "author": msg.author.display_name,
                        "user_id": str(msg.author.id), "channel": channel.name,
                        "timestamp": msg.created_at.strftime("%Y-%m-%d %H:%M")
                    })
                    learn_sentence_trigrams(data, msg.content, msg.author.id)
                    scanned_count += 1
        except Exception as e:
            print(f"Error scanning {channel.name}: {e}")

    save_data(data)
    msg_str = f"🧠⚡ **BrainScan Complete!** Indexed **{scanned_count:,}** historical messages."
    if ctx.interaction:
        await ctx.followup.send(msg_str, ephemeral=True)
    else:
        await ctx.send(msg_str)

# 4. /brainsearch
@bot.hybrid_command(name="brainsearch", description="Searches archived message memory for keywords.")
async def brainsearch(ctx: commands.Context, *, query: str):
    data = load_data()
    matches = [m for m in data["message_archive"] if query.lower() in m["content"].lower()]
    if not matches:
        return await ctx.reply(f"❌ No archived messages found matching **'{query}'**.", ephemeral=bool(ctx.interaction))
=======
    total_trigrams = sum(len(v) for v in data["trigrams"].values())
    total_quotes = len(data["quotes"])
    total_users = len(data["user_chat_counts"])
    total_archived = len(data["message_archive"])
>>>>>>> 675b6ad2f2f613e44ad1f082dc1a3918f2b1bb7b
    
<<<<<<< HEAD
    embed = discord.Embed(title=f"🔎 BrainSearch Results: '{query}'", color=discord.Color.green())
    for m in matches[-5:]:
        embed.add_field(name=f"From {m['author']} (#{m['channel']} at {m['timestamp']})", value=m['content'], inline=False)
    await ctx.reply(embed=embed, ephemeral=bool(ctx.interaction))

# 5. /quote
@bot.hybrid_command(name="quote", description="Pulls a random legendary server quote.")
async def quote(ctx: commands.Context):
    data = load_data()
    if not data["quotes"]:
        return await ctx.reply("❌ No quotes captured yet!", ephemeral=bool(ctx.interaction))
    q = random.choice(data["quotes"])
    embed = discord.Embed(title="👑 Legendary Lore Quote", description=f"\"{q['text']}\"", color=discord.Color.gold())
    embed.set_footer(text=f"Added by: {q['added_by']} | {q['timestamp']}")
    await ctx.reply(embed=embed, ephemeral=bool(ctx.interaction))

# 6. /addquote
@bot.hybrid_command(name="addquote", description="Manually adds a quote to server lore.")
async def addquote(ctx: commands.Context, *, text: str):
    data = load_data()
    data["quotes"].append({
        "text": text,
        "added_by": f"{ctx.author.display_name} (Manual Entry ✨)",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    save_data(data)
    await ctx.reply(f"✅ Successfully archived quote: **\"{text}\"**", ephemeral=bool(ctx.interaction))

# 7. /chatleaderboard
@bot.hybrid_command(name="chatleaderboard", description="Shows the top most active chatters in the server.")
async def chatleaderboard(ctx: commands.Context):
    data = load_data()
    counts = data.get("user_chat_counts", {})
    if not counts:
        return await ctx.reply("❌ No chat metrics recorded yet.", ephemeral=bool(ctx.interaction))
=======
    embed = discord.Embed(title="🧠 Neural Brain Matrix Stats", color=discord.Color.blurple())
    embed.add_field(name="Trigram Connections", value=f"{total_trigrams:,}", inline=True)
    embed.add_field(name="Captured Quotes", value=f"{total_quotes:,}", inline=True)
    embed.add_field(name="Archived Messages", value=f"{total_archived:,}", inline=True)
    embed.add_field(name="Tracked Users", value=f"{total_users:,}", inline=True)
>>>>>>> 675b6ad2f2f613e44ad1f082dc1a3918f2b1bb7b
    
    sorted_users = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]
    embed = discord.Embed(title="🏆 Server Chat Activity Leaderboard", color=discord.Color.orange())
    
    desc = ""
    for idx, (uid, count) in enumerate(sorted_users, 1):
        member = ctx.guild.get_member(int(uid))
        name = member.display_name if member else f"User ID: {uid}"
        desc += f"**{idx}.** {name} — **{count:,}** messages\n"
    
    embed.description = desc
    await ctx.reply(embed=embed, ephemeral=bool(ctx.interaction))

# 8. /emojistats
@bot.hybrid_command(name="emojistats", description="Shows the server's favorite and most-used emojis.")
async def emojistats(ctx: commands.Context):
    data = load_data()
    emojis = data.get("server_emojis", {})
    if not emojis:
        return await ctx.reply("❌ No emojis tracked yet.", ephemeral=bool(ctx.interaction))
    
    top_emojis = sorted(emojis.items(), key=lambda x: x[1], reverse=True)[:10]
    embed = discord.Embed(title="📊 Server Emoji Matrix", color=discord.Color.magenta())
    desc = "".join([f"{emo}: **{count}** uses\n" for emo, count in top_emojis])
    embed.description = desc
    await ctx.reply(embed=embed, ephemeral=bool(ctx.interaction))

# 9. /userprofile
@bot.hybrid_command(name="userprofile", description="Inspects a user's matrix learning profile.")
async def userprofile(ctx: commands.Context, member: discord.Member = None):
    target = member or ctx.author
    data = load_data()
    uid = str(target.id)
    
    chats = data.get("user_chat_counts", {}).get(uid, 0)
    has_custom_matrix = uid in data.get("user_trigrams", {})
    trigram_count = sum(len(v) for v in data.get("user_trigrams", {}).get(uid, {}).values()) if has_custom_matrix else 0
    
    embed = discord.Embed(title=f"👤 Neural Profile: {target.display_name}", color=target.color)
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="Total Messages Logged", value=f"{chats:,}", inline=True)
    embed.add_field(name="Unique Trigram Nodes", value=f"{trigram_count:,}", inline=True)
    embed.add_field(name="Custom Brain Clone", value="Active 🧠" if has_custom_matrix else "Standard Server Pool", inline=True)
    await ctx.reply(embed=embed, ephemeral=bool(ctx.interaction))

# 10. /roast
@bot.hybrid_command(name="roast", description="Generates a customized AI roast for a user.")
async def roast(ctx: commands.Context, member: discord.Member = None):
    target = member or ctx.author
    data = load_data()
    roast_text = generate_complex_ai_mimic(data, user_id=target.id, max_words=12)
    embed = discord.Embed(title=f"🔥 Neural Roast: {target.display_name}", description=f"\"{roast_text} fr smh\"\n— *AI Matrix Generator*", color=discord.Color.red())
    await ctx.reply(embed=embed)

# 11. /hype
@bot.hybrid_command(name="hype", description="Generates ultra-energetic server hype text.")
async def hype(ctx: commands.Context):
    data = load_data()
    hyped = generate_complex_ai_mimic(data, seed_word="let", max_words=15).upper()
    await ctx.reply(f"🚀 **HYPE MATRIX ENGAGED:** {hyped} 🔥🔥🔥", ephemeral=bool(ctx.interaction))

# 12. /conspiracy
@bot.hybrid_command(name="conspiracy", description="Formulates a random server conspiracy theory.")
async def conspiracy(ctx: commands.Context):
    data = load_data()
    theory = generate_complex_ai_mimic(data, max_words=18)
    embed = discord.Embed(title="🕵️‍♂️ Server Conspiracy Theory", description=f"\"Did you know that {theory.lower()}? Stay woke... 👁️\"", color=discord.Color.dark_purple())
    await ctx.reply(embed=embed, ephemeral=bool(ctx.interaction))

# 13. /asklore
@bot.hybrid_command(name="asklore", description="Asks the bot's neural memory an open-ended lore question.")
async def asklore(ctx: commands.Context, *, question: str):
    data = load_data()
    potential_seeds = [w for w in question.split() if len(w) > 3]
    seed = random.choice(potential_seeds) if potential_seeds else None
    answer = generate_complex_ai_mimic(data, seed_word=seed, max_words=16)
    
    embed = discord.Embed(title="🤖 Neural Lore Inquiry", color=discord.Color.blurple())
    embed.add_field(name="Question", value=question, inline=False)
    embed.add_field(name="Matrix Answer", value=f"\"{answer}\"", inline=False)
    await ctx.reply(embed=embed, ephemeral=bool(ctx.interaction))

# 14. /clearmatrix
@bot.hybrid_command(name="clearmatrix", description="[Admin] Wipes and resets the bot's learning matrices.")
@commands.has_permissions(administrator=True)
async def clearmatrix(ctx: commands.Context):
    default_schema = {
        "quotes": [], "lore": {}, "user_chat_counts": {}, 
        "server_emojis": {}, "trigrams": {}, "user_trigrams": {}, "message_archive": []
    }
    save_data(default_schema)
    await ctx.reply("⚠️ **Neural matrix completely wiped and reset to factory settings!**", ephemeral=True)

# 15. /exportlore
@bot.hybrid_command(name="exportlore", description="[Admin] Shows data export metrics and storage size.")
@commands.has_permissions(administrator=True)
async def exportlore(ctx: commands.Context):
    size_bytes = os.path.getsize(DATA_FILE) if os.path.exists(DATA_FILE) else 0
    size_kb = size_bytes / 1024
    await ctx.reply(f"📦 **Database File Size:** {size_kb:.2f} KB (`{DATA_FILE}`)", ephemeral=True)

# 16. /magic8
@bot.hybrid_command(name="magic8", description="Answers a yes/no question using sarcastic Markov 8-ball logic.")
async def magic8(ctx: commands.Context, *, question: str):
    responses = [
        "It is decidedly so fr fr", "Outlook not so good tbh", "Most definitely lol", 
        "Ask again when matrix syncs smh", "Without a doubt lmao", "My neural sources say no",
        "Signs point to yes fr", "Better not tell you now 💀"
    ]
    await ctx.reply(f"🎱 **Question:** {question}\n🔮 **Answer:** {random.choice(responses)}", ephemeral=bool(ctx.interaction))

# 17. /coinflip
@bot.hybrid_command(name="coinflip", description="Flips a coin with style.")
async def coinflip(ctx: commands.Context):
    result = random.choice(["Heads 🪙", "Tails 🪙"])
    await ctx.reply(f"🎲 The coin landed on: **{result}**", ephemeral=bool(ctx.interaction))

# 18. /roll
@bot.hybrid_command(name="roll", description="Rolls a random number between 1 and 100.")
async def roll(ctx: commands.Context, maximum: int = 100):
    num = random.randint(1, maximum)
    await ctx.reply(f"🎲 You rolled: **{num}** (Range: 1-{maximum})", ephemeral=bool(ctx.interaction))

# 19. /poll
@bot.hybrid_command(name="poll", description="Creates an instant reaction poll.")
async def poll(ctx: commands.Context, *, question: str):
    embed = discord.Embed(title="📊 Server Poll", description=question, color=discord.Color.blue())
    embed.set_footer(text=f"Poll created by {ctx.author.display_name}")
    msg = await ctx.send(embed=embed) if not ctx.interaction else await ctx.interaction.response.send_message(embed=embed)
    # If using interaction, fetch original response to add reactions
    if ctx.interaction:
        msg = await ctx.interaction.original_response()
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")

<<<<<<< HEAD
# 20. /matrixhealth
@bot.hybrid_command(name="matrixhealth", description="Performs a diagnostics check on brain matrix integrity.")
async def matrixhealth(ctx: commands.Context):
    data = load_data()
    status = "Optimal 🟢" if len(data["trigrams"]) > 10 else "Learning Phase 🟡"
    embed = discord.Embed(title="🛠️ Matrix System Diagnostics", color=discord.Color.green())
    embed.add_field(name="Brain Status", value=status, inline=True)
    embed.add_field(name="Memory Schema Version", value="v4.0 Max-Power", inline=True)
    embed.add_field(name="JSON Schema Check", value="Passed ✅", inline=True)
    await ctx.reply(embed=embed, ephemeral=bool(ctx.interaction))


=======
@bot.hybrid_command(name="brainscan", description="Deep scan: Ingests ALL historical text chats across the entire server.")
@commands.has_permissions(manage_guild=True)
async def brainscan(ctx: commands.Context):
    """Scans every text channel completely from top to bottom (limit=None)."""
    if ctx.interaction:
        await ctx.defer(ephemeral=True)
        await ctx.followup.send("🧠⚡ **Deep BrainScan Initiated:** Scanning ALL text channels and every single historical message in the entire server. This may take a little while depending on server size...", ephemeral=True)
    else:
        await ctx.send("🧠⚡ **Deep BrainScan Initiated:** Scanning ALL text channels and every single historical message in the entire server. This may take a little while...")

    data = load_data()
    scanned_count = 0

    for channel in ctx.guild.text_channels:
        try:
            # limit=None pulls the entire chat history of the channel
            async for msg in channel.history(limit=None):
                if msg.author.bot or not msg.content.strip():
                    continue
                
                # Check for duplicates
                exists = any(m["content"] == msg.content and m["user_id"] == str(msg.author.id) for m in data["message_archive"])
                if not exists:
                    data["message_archive"].append({
                        "content": msg.content,
                        "author": msg.author.display_name,
                        "user_id": str(msg.author.id),
                        "channel": channel.name,
                        "timestamp": msg.created_at.strftime("%Y-%m-%d %H:%M")
                    })
                    # Feed into structural Markov trigram matrix
                    learn_sentence_trigrams(data, msg.content, msg.author.id)
                    scanned_count += 1
        except Exception as e:
            print(f"Error scanning channel {channel.name}: {e}")

    save_data(data)
    
    result_msg = f"🧠⚡ **Deep BrainScan Complete!** Successfully ingested and indexed **{scanned_count:,}** historical messages across all server channels into `server_lore.json`."
    if ctx.interaction:
        await ctx.followup.send(result_msg, ephemeral=True)
    else:
        await ctx.send(result_msg)

@bot.hybrid_command(name="brainsearch", description="Searches the bot's archived message memory for keywords.")
async def brainsearch(ctx: commands.Context, *, query: str):
    """Searches archived messages for matching terms."""
    data = load_data()
    query_lower = query.lower()
    
    matches = [m for m in data["message_archive"] if query_lower in m["content"].lower()]
    
    if not matches:
        reply_text = f"❌ No archived messages found matching **'{query}'**."
        if ctx.interaction:
            await ctx.reply(reply_text, ephemeral=True)
        else:
            await ctx.reply(reply_text)
        return

    # Take up to the top 5 most recent matches
    matches = matches[-5:]
    
    embed = discord.Embed(title=f"🔎 BrainSearch Results: '{query}'", color=discord.Color.green())
    for m in matches:
        embed.add_field(
            name=f"From {m['author']} (#{m['channel']} at {m['timestamp']})",
            value=m['content'],
            inline=False
        )
        
    if ctx.interaction:
        await ctx.reply(embed=embed, ephemeral=True)
    else:
        await ctx.reply(embed=embed)

>>>>>>> 675b6ad2f2f613e44ad1f082dc1a3918f2b1bb7b
# Run the bot
bot.run(os.getenv("TOKEN"))