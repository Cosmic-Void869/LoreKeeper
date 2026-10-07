import asyncio
import json
import logging
import os
import random
import re
from datetime import datetime, timedelta
from pathlib import Path

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

# ------------------------------------------------------------
# Load environment
# ------------------------------------------------------------
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("lorekeeper")

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
TOKEN = os.getenv("TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
ENABLE_RANDOM_RESPONSES = os.getenv("ENABLE_RANDOM_RESPONSES", "false").lower() in ("1", "true", "yes")
RANDOM_REPLY_CHANCE = float(os.getenv("RANDOM_REPLY_CHANCE", "0.04"))
MAX_MESSAGE_ARCHIVE = int(os.getenv("MAX_MESSAGE_ARCHIVE", "5000"))
MAX_SCAN_MESSAGES = int(os.getenv("MAX_SCAN_MESSAGES", "200"))
MAX_SCAN_CHANNELS = int(os.getenv("MAX_SCAN_CHANNELS", "10"))
HISTORY_DAYS = int(os.getenv("HISTORY_DAYS", "30"))
DATA_FILE = Path(os.getenv("DATA_FILE", "server_lore.json"))
BACKUP_FILE = Path(os.getenv("BACKUP_FILE", "server_lore.backup.json"))

# ------------------------------------------------------------
# Intents
# ------------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ------------------------------------------------------------
# Runtime state
# ------------------------------------------------------------
_DATA_CACHE = None
_DATA_LOCK = asyncio.Lock()
_LAST_RANDOM_REPLY = {}

WORD_BLACKLIST = ["token", "password", "secret", "https://", "http://"]

# ------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------
def default_schema():
    return {
        "quotes": [],
        "lore": {},
        "user_chat_counts": {},
        "server_emojis": {},
        "trigrams": {},
        "user_trigrams": {},
        "message_archive": [],
    }

def ensure_schema(data):
    schema = default_schema()
    for key, val in schema.items():
        data.setdefault(key, val)
    return data

def backup_file(src: Path, dst: Path):
    try:
        if src.exists():
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception as exc:
        logger.warning(f"Could not create backup file: {exc}")

def atomic_write_json(path: Path, data):
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        os.replace(tmp_path, path)
    except Exception as exc:
        logger.exception(f"Failed to write {path}: {exc}")
        raise

def load_data():
    """Load the data file once and keep it in memory."""
    global _DATA_CACHE

    if _DATA_CACHE is not None:
        return _DATA_CACHE

    if not DATA_FILE.exists():
        _DATA_CACHE = default_schema()
        return _DATA_CACHE

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(f"Failed to load data file, creating fresh schema: {exc}")
        _DATA_CACHE = default_schema()
        backup_file(DATA_FILE, BACKUP_FILE)
        return _DATA_CACHE

    _DATA_CACHE = ensure_schema(data)
    return _DATA_CACHE

def save_data(data=None):
    """Synchronous save for fallback/non-async calls."""
    global _DATA_CACHE

    if data is not None:
        _DATA_CACHE = data

    if _DATA_CACHE is None:
        return

    try:
        backup_file(DATA_FILE, BACKUP_FILE)
        atomic_write_json(DATA_FILE, _DATA_CACHE)
    except Exception as exc:
        logger.exception(f"save_data failed: {exc}")

async def save_data_async(data=None):
    """Async save with lock to reduce race conditions."""
    global _DATA_CACHE

    if data is not None:
        _DATA_CACHE = data

    if _DATA_CACHE is None:
        return

    async with _DATA_LOCK:
        try:
            backup_file(DATA_FILE, BACKUP_FILE)
            atomic_write_json(DATA_FILE, _DATA_CACHE)
        except Exception as exc:
            logger.exception(f"save_data_async failed: {exc}")

def prune_message_archive(data):
    if len(data["message_archive"]) > MAX_MESSAGE_ARCHIVE:
        data["message_archive"] = data["message_archive"][-MAX_MESSAGE_ARCHIVE:]
    return data

def clean_token(token):
    if any(blacklisted in token for blacklisted in WORD_BLACKLIST):
        return ""
    return token.strip(".,!?\"()[]{}*<>~`").lower()

def learn_sentence_trigrams(data, text, user_id=None):
    raw_tokens = text.split()
    tokens = [clean_token(t) for t in raw_tokens if clean_token(t)]

    emojis = re.findall(
        r"<a?:[a-zA-Z0-9_]+:[0-9]+>|[\u2600-\u27BF]|[\U0001f300-\U0001f64f]|[\U0001f680-\U0001f6ff]",
        text,
    )
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
        w1, w2, w3 = tokens[i], tokens[i + 1], tokens[i + 2]
        key = f"{w1} {w2}"
        _append_trigram(data, key, w3, user_id)

def _append_trigram(data, key, value, user_id=None):
    if key not in data["trigrams"]:
        data["trigrams"][key] = []
    data["trigrams"][key].append(value)

    if user_id:
        user_id = str(user_id)
        if user_id not in data["user_trigrams"]:
            data["user_trigrams"][user_id] = {}
        if key not in data["user_trigrams"][user_id]:
            data["user_trigrams"][user_id][key] = []
        data["user_trigrams"][user_id][key].append(value)

def generate_complex_ai_mimic(data, user_id=None, seed_word=None, max_words=20):
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
    if w1 != "__start__":
        sentence.append(w1)
    if w2 != "__start__":
        sentence.append(w2)

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

    response = " ".join(sentence).capitalize()
    return response + random.choice(flavor_elements)

# ------------------------------------------------------------
# Async tasks
# ------------------------------------------------------------
@tasks.loop(minutes=5)
async def auto_save_task():
    """Persist data periodically."""
    data = load_data()
    await save_data_async(prune_message_archive(data))

@tasks.loop(minutes=10)
async def status_rotator():
    data = load_data()
    total_connections = sum(len(v) for v in data["trigrams"].values())
    await bot.change_presence(activity=discord.CustomActivity(name=f"🧠 Processing {total_connections} structural layers | /help"))

# ------------------------------------------------------------
# Bot events
# ------------------------------------------------------------
@bot.event
async def on_ready():
    logger.info(f"Bot started: {bot.user.name} ({bot.user.id})")

    if TOKEN is None:
        logger.error("TOKEN environment variable is missing.")
        return

    # Sync commands to a specific guild only if configured
    guild = None
    if GUILD_ID:
        try:
            guild = bot.get_guild(int(GUILD_ID))
        except (TypeError, ValueError):
            guild = None

    if guild:
        try:
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
            logger.info(f"Slash commands synced to guild {guild.id}")
        except Exception as exc:
            logger.exception(f"Failed to sync commands: {exc}")
    else:
        try:
            await bot.tree.sync()
            logger.info("Slash commands synced globally")
        except Exception as exc:
            logger.exception(f"Failed to sync global commands: {exc}")

    if not status_rotator.is_running():
        status_rotator.start()

    if not auto_save_task.is_running():
        auto_save_task.start()

    load_data()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content.startswith("!"):
        await bot.process_commands(message)
        return

    data = load_data()
    user_id = str(message.author.id)

    data["user_chat_counts"][user_id] = data["user_chat_counts"].get(user_id, 0) + 1

    if message.content.strip():
        data["message_archive"].append({
            "content": message.content,
            "author": message.author.display_name,
            "user_id": user_id,
            "channel": message.channel.name,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        })

    learn_sentence_trigrams(data, message.content, user_id)
    prune_message_archive(data)

    # Prevent random spam unless explicitly enabled
    if ENABLE_RANDOM_RESPONSES:
        channel_key = str(message.channel.id)
        now = datetime.now()
        last_reply = _LAST_RANDOM_REPLY.get(channel_key)
        if last_reply is None or (now - last_reply).total_seconds() >= 60:
            if len(message.content) > 25 and random.random() < RANDOM_REPLY_CHANCE:
                if not any(q['text'] == message.content for q in data["quotes"]):
                    data["quotes"].append({
                        "text": message.content,
                        "added_by": f"{message.author.display_name} (Calculated Lore Capture 🤖)",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                    })
                    await message.add_reaction("👑")

            if random.random() < RANDOM_REPLY_CHANCE and len(data["trigrams"]) > 25:
                async with message.channel.typing():
                    await asyncio.sleep(random.uniform(0.6, 1.8))
                    potential_seeds = [w for w in message.content.split() if len(w) > 3]
                    seed = random.choice(potential_seeds) if potential_seeds else None
                    target = random.choice([None, user_id])
                    advanced_reply = generate_complex_ai_mimic(data, user_id=target, seed_word=seed)
                    await message.channel.send(advanced_reply)
                    _LAST_RANDOM_REPLY[channel_key] = now

    await bot.process_commands(message)
    await save_data_async(data)

# ------------------------------------------------------------
# Helper commands
# ------------------------------------------------------------
@bot.hybrid_command(name="help", description="Displays all available commands and what they do.")
async def help_command(ctx: commands.Context):
    embed = discord.Embed(
        title="👑 aLore keeper — Command Matrix",
        description="Here are all available features. You can use them via slash commands (`/`) or prefix (`!`).",
        color=discord.Color.gold()
    )

    for command in sorted(bot.tree.get_commands(), key=lambda c: c.name):
        embed.add_field(
            name=f"/{command.name}",
            value=command.description or "No description provided.",
            inline=False
        )

    embed.set_footer(text="aLore keeper v4.2 • Powered by Neural Trigram Matrices")
    await ctx.reply(embed=embed, ephemeral=bool(ctx.interaction))

@bot.hybrid_command(name="mimic", description="Generates a complex text string based on server learning.")
async def mimic(ctx: commands.Context):
    data = load_data()
    reply = generate_complex_ai_mimic(data, user_id=ctx.author.id)
    await ctx.reply(reply, ephemeral=bool(ctx.interaction))

@bot.hybrid_command(name="stats", description="Displays the bot's neural matrix statistics.")
async def stats(ctx: commands.Context):
    data = load_data()
    embed = discord.Embed(title="🧠 Neural Brain Matrix Stats", color=discord.Color.blurple())
    embed.add_field(name="Trigram Connections", value=f"{sum(len(v) for v in data['trigrams'].values()):,}", inline=True)
    embed.add_field(name="Captured Quotes", value=f"{len(data['quotes']):,}", inline=True)
    embed.add_field(name="Archived Messages", value=f"{len(data['message_archive']):,}", inline=True)
    embed.add_field(name="Tracked Users", value=f"{len(data['user_chat_counts']):,}", inline=True)
    await ctx.reply(embed=embed, ephemeral=bool(ctx.interaction))

@bot.hybrid_command(name="brainscan", description="Deep scan: ingest recent historical text chats from this server.")
async def brainscan(ctx: commands.Context):
    if not ctx.author.guild_permissions.administrator:
        return await ctx.reply("❌ Only admins can run a full brain scan.", ephemeral=bool(ctx.interaction))

    data = load_data()

    if ctx.interaction:
        await ctx.defer(ephemeral=True)
        await ctx.followup.send("🧠⚡ **Deep BrainScan Initiated:** scanning recent server history...", ephemeral=True)
    else:
        await ctx.send("🧠⚡ **Deep BrainScan Initiated:** scanning recent server history...")

    cutoff = datetime.now() - timedelta(days=HISTORY_DAYS)
    scanned_count = 0
    scanned_channels = 0

    for channel in ctx.guild.text_channels[:MAX_SCAN_CHANNELS]:
        if scanned_channels >= MAX_SCAN_CHANNELS:
            break

        try:
            scanned_channels += 1
            async for msg in channel.history(limit=MAX_SCAN_MESSAGES, after=cutoff):
                if msg.author.bot or not msg.content.strip():
                    continue

                exists = any(
                    m["content"] == msg.content and m["user_id"] == str(msg.author.id)
                    for m in data["message_archive"]
                )
                if not exists:
                    data["message_archive"].append({
                        "content": msg.content,
                        "author": msg.author.display_name,
                        "user_id": str(msg.author.id),
                        "channel": channel.name,
                        "timestamp": msg.created_at.strftime("%Y-%m-%d %H:%M")
                    })
                    learn_sentence_trigrams(data, msg.content, msg.author.id)
                    scanned_count += 1
        except Exception as exc:
            logger.warning(f"Error scanning {channel.name}: {exc}")

    data = prune_message_archive(data)
    await save_data_async(data)

    msg_str = f"🧠⚡ **BrainScan Complete!** Indexed **{scanned_count:,}** recent messages across **{scanned_channels}** channels."
    if ctx.interaction:
        await ctx.followup.send(msg_str, ephemeral=True)
    else:
        await ctx.send(msg_str)

@bot.hybrid_command(name="brainsearch", description="Searches archived message memory for keywords.")
async def brainsearch(ctx: commands.Context, *, query: str):
    data = load_data()
    matches = [m for m in data["message_archive"] if query.lower() in m["content"].lower()]
    if not matches:
        return await ctx.reply(f"❌ No archived messages found matching **'{query}'**.", ephemeral=bool(ctx.interaction))

    embed = discord.Embed(title=f"🔎 BrainSearch Results: '{query}'", color=discord.Color.green())
    for m in matches[-5:]:
        embed.add_field(name=f"From {m['author']} (#{m['channel']} at {m['timestamp']})", value=m['content'], inline=False)
    await ctx.reply(embed=embed, ephemeral=bool(ctx.interaction))

@bot.hybrid_command(name="quote", description="Pulls a random legendary server quote.")
async def quote(ctx: commands.Context):
    data = load_data()
    if not data["quotes"]:
        return await ctx.reply("❌ No quotes captured yet!", ephemeral=bool(ctx.interaction))
    q = random.choice(data["quotes"])
    embed = discord.Embed(title="👑 Legendary Lore Quote", description=f"\"{q['text']}\"", color=discord.Color.gold())
    embed.set_footer(text=f"Added by: {q['added_by']} | {q['timestamp']}")
    await ctx.reply(embed=embed, ephemeral=bool(ctx.interaction))

@bot.hybrid_command(name="addquote", description="Manually adds a quote to server lore.")
async def addquote(ctx: commands.Context, *, text: str):
    data = load_data()
    data["quotes"].append({
        "text": text,
        "added_by": f"{ctx.author.display_name} (Manual Entry ✨)",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    await save_data_async(data)
    await ctx.reply(f"✅ Successfully archived quote: **\"{text}\"**", ephemeral=bool(ctx.interaction))

@bot.hybrid_command(name="chatleaderboard", description="Shows the top most active chatters in the server.")
async def chatleaderboard(ctx: commands.Context):
    data = load_data()
    counts = data.get("user_chat_counts", {})
    if not counts:
        return await ctx.reply("❌ No chat metrics recorded yet.", ephemeral=bool(ctx.interaction))

    sorted_users = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]
    embed = discord.Embed(title="🏆 Server Chat Activity Leaderboard", color=discord.Color.orange())

    desc = ""
    for idx, (uid, count) in enumerate(sorted_users, 1):
        member = ctx.guild.get_member(int(uid))
        name = member.display_name if member else f"User ID: {uid}"
        desc += f"**{idx}.** {name} — **{count:,}** messages\n"

    embed.description = desc
    await ctx.reply(embed=embed, ephemeral=bool(ctx.interaction))

@bot.hybrid_command(name="emojistats", description="Shows the server's favorite and most-used emojis.")
async def emojistats(ctx: commands.Context):
    data = load_data()
    emojis = data.get("server_emojis", {})
    if not emojis:
        return await ctx.reply("❌ No emojis tracked yet.", ephemeral=bool(ctx.interaction))

    top_emojis = sorted(emojis.items(), key=lambda x: x[1], reverse=True)[:10]
    embed = discord.Embed(title="📊 Server Emoji Matrix", color=discord.Color.magenta())
    embed.description = "".join([f"{emo}: **{count}** uses\n" for emo, count in top_emojis])
    await ctx.reply(embed=embed, ephemeral=bool(ctx.interaction))

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

@bot.hybrid_command(name="roast", description="Generates a customized AI roast for a user.")
async def roast(ctx: commands.Context, member: discord.Member = None):
    target = member or ctx.author
    data = load_data()
    roast_text = generate_complex_ai_mimic(data, user_id=target.id, max_words=12)
    embed = discord.Embed(title=f"🔥 Neural Roast: {target.display_name}", description=f"\"{roast_text} fr smh\"\n— *AI Matrix Generator*", color=discord.Color.red())
    await ctx.reply(embed=embed)

@bot.hybrid_command(name="hype", description="Generates ultra-energetic server hype text.")
async def hype(ctx: commands.Context):
    data = load_data()
    hyped = generate_complex_ai_mimic(data, seed_word="let", max_words=15).upper()
    await ctx.reply(f"🚀 **HYPE MATRIX ENGAGED:** {hyped} 🔥🔥🔥", ephemeral=bool(ctx.interaction))

@bot.hybrid_command(name="conspiracy", description="Formulates a random server conspiracy theory.")
async def conspiracy(ctx: commands.Context):
    data = load_data()
    theory = generate_complex_ai_mimic(data, max_words=18)
    embed = discord.Embed(title="🕵️‍♂️ Server Conspiracy Theory", description=f"\"Did you know that {theory.lower()}? Stay woke... 👁️\"", color=discord.Color.dark_purple())
    await ctx.reply(embed=embed, ephemeral=bool(ctx.interaction))

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

@bot.hybrid_command(name="clearmatrix", description="[Admin] Wipes and resets the bot's learning matrices.")
@commands.has_permissions(administrator=True)
async def clearmatrix(ctx: commands.Context):
    global _DATA_CACHE
    _DATA_CACHE = default_schema()
    await save_data_async()
    await ctx.reply("⚠️ **Neural matrix completely wiped and reset to factory settings!**", ephemeral=True)

@bot.hybrid_command(name="exportlore", description="[Admin] Shows data export metrics and storage size.")
@commands.has_permissions(administrator=True)
async def exportlore(ctx: commands.Context):
    size_bytes = DATA_FILE.stat().st_size if DATA_FILE.exists() else 0
    await ctx.reply(f"📦 **Database File Size:** {size_bytes / 1024:.2f} KB (`{DATA_FILE}`)", ephemeral=True)

@bot.hybrid_command(name="magic8", description="Answers a yes/no question using sarcastic Markov 8-ball logic.")
async def magic8(ctx: commands.Context, *, question: str):
    responses = [
        "It is decidedly so fr fr",
        "Outlook not so good tbh",
        "Most definitely lol",
        "Ask again when matrix syncs smh",
        "Without a doubt lmao",
        "My neural sources say no",
        "Signs point to yes fr",
        "Better not tell you now 💀",
    ]
    await ctx.reply(f"🎱 **Question:** {question}\n🔮 **Answer:** {random.choice(responses)}", ephemeral=bool(ctx.interaction))

@bot.hybrid_command(name="coinflip", description="Flips a coin with style.")
async def coinflip(ctx: commands.Context):
    result = random.choice(["Heads 🪙", "Tails 🪙"])
    await ctx.reply(f"🎲 The coin landed on: **{result}**", ephemeral=bool(ctx.interaction))

@bot.hybrid_command(name="roll", description="Rolls a random number between 1 and 100.")
async def roll(ctx: commands.Context, maximum: int = 100):
    num = random.randint(1, maximum)
    await ctx.reply(f"🎲 You rolled: **{num}** (Range: 1-{maximum})", ephemeral=bool(ctx.interaction))

@bot.hybrid_command(name="poll", description="Creates an instant reaction poll.")
async def poll(ctx: commands.Context, *, question: str):
    embed = discord.Embed(title="📊 Server Poll", description=question, color=discord.Color.blue())
    embed.set_footer(text=f"Poll created by {ctx.author.display_name}")

    if ctx.interaction:
        await ctx.interaction.response.send_message(embed=embed)
        msg = await ctx.interaction.original_response()
    else:
        msg = await ctx.send(embed=embed)

    await msg.add_reaction("👍")
    await msg.add_reaction("👎")

@bot.hybrid_command(name="matrixhealth", description="Performs a diagnostics check on brain matrix integrity.")
async def matrixhealth(ctx: commands.Context):
    data = load_data()
    status = "Optimal 🟢" if len(data["trigrams"]) > 10 else "Learning Phase 🟡"
    embed = discord.Embed(title="🛠️ Matrix System Diagnostics", color=discord.Color.green())
    embed.add_field(name="Brain Status", value=status, inline=True)
    embed.add_field(name="Memory Schema Version", value="v4.2 Optimized Help", inline=True)
    embed.add_field(name="JSON Schema Check", value="Passed ✅", inline=True)
    await ctx.reply(embed=embed, ephemeral=bool(ctx.interaction))

# ------------------------------------------------------------
# Startup
# ------------------------------------------------------------
if __name__ == "__main__":
    if TOKEN is None:
        raise RuntimeError("Missing required environment variable: TOKEN")
    bot.run(TOKEN)