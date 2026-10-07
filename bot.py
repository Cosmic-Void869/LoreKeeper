import asyncio
import json
import logging
import os
import random
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

# ============================================================
# Environment & Logging Setup
# ============================================================
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/app/data/lorekeeper.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("lorekeeper")

# ============================================================
# Configuration & Validation
# ============================================================
def load_config():
    """Load and validate all configuration from environment."""
    data_dir = Path(os.getenv("DATA_DIR", "/app/data"))
    data_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "token": os.getenv("TOKEN") or os.getenv("DISCORD_TOKEN"),
        "guild_id": os.getenv("GUILD_ID"),
        "enable_random_responses": os.getenv("ENABLE_RANDOM_RESPONSES", "false").lower() in ("1", "true", "yes"),
        "random_reply_chance": float(os.getenv("RANDOM_REPLY_CHANCE", "0.04")),
        "max_message_archive": int(os.getenv("MAX_MESSAGE_ARCHIVE", "5000")),
        "max_scan_messages": int(os.getenv("MAX_SCAN_MESSAGES", "200")),
        "max_scan_channels": int(os.getenv("MAX_SCAN_CHANNELS", "10")),
        "history_days": int(os.getenv("HISTORY_DAYS", "30")),
        "data_file": data_dir / "server_lore.json",
        "backup_file": data_dir / "server_lore.backup.json",
        "command_cooldown": int(os.getenv("COMMAND_COOLDOWN", "3")),
    }

    # Validate critical config
    if not config["token"]:
        logger.error("❌ Missing TOKEN or DISCORD_TOKEN environment variable")
        sys.exit(1)

    if config["random_reply_chance"] < 0 or config["random_reply_chance"] > 1:
        logger.error("❌ RANDOM_REPLY_CHANCE must be between 0 and 1")
        sys.exit(1)

    if config["max_message_archive"] < 100:
        logger.warning("⚠️  MAX_MESSAGE_ARCHIVE is very low (<100)")

    logger.info("✅ Configuration loaded successfully")
    logger.info(f"📁 Data directory: {data_dir}")
    return config

CONFIG = load_config()

# ============================================================
# Discord Setup
# ============================================================
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ============================================================
# Runtime State
# ============================================================
_DATA_CACHE: Optional[dict] = None
_DATA_LOCK = asyncio.Lock()
_COMMAND_COOLDOWNS = {}
_LAST_RANDOM_REPLY = {}

WORD_BLACKLIST = ["token", "password", "secret", "https://", "http://"]

# ============================================================
# Data File Helpers (AUTO-CREATE)
# ============================================================
def default_schema() -> dict:
    """Return the default data schema."""
    return {
        "quotes": [],
        "lore": {},
        "user_chat_counts": {},
        "server_emojis": {},
        "trigrams": {},
        "user_trigrams": {},
        "message_archive": [],
        "last_updated": datetime.now().isoformat(),
    }

def ensure_schema(data: dict) -> dict:
    """Ensure all required schema keys exist."""
    schema = default_schema()
    for key, val in schema.items():
        data.setdefault(key, val)
    return data

def ensure_data_file():
    """Create server_lore.json if it doesn't exist."""
    global _DATA_CACHE
    
    if CONFIG["data_file"].exists():
        logger.info(f"📁 Data file found: {CONFIG['data_file']}")
        return
    
    logger.info(f"📁 Creating new data file: {CONFIG['data_file']}")
    default_data = default_schema()
    try:
        CONFIG["data_file"].write_text(
            json.dumps(default_data, indent=4, ensure_ascii=False),
            encoding="utf-8"
        )
        logger.info("✅ Data file created successfully")
        _DATA_CACHE = default_data
    except Exception as exc:
        logger.error(f"❌ Failed to create data file: {exc}")
        raise

# ============================================================
# Utility Functions
# ============================================================
def check_command_cooldown(user_id: int, cooldown_seconds: int = CONFIG["command_cooldown"]) -> bool:
    """Check if a user is on cooldown."""
    now = datetime.now()
    last_used = _COMMAND_COOLDOWNS.get(user_id)

    if last_used is None or (now - last_used).total_seconds() >= cooldown_seconds:
        _COMMAND_COOLDOWNS[user_id] = now
        return False
    return True

def backup_file(src: Path, dst: Path):
    """Create a backup of the source file."""
    try:
        if src.exists():
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            logger.debug(f"Backup created: {dst}")
    except Exception as exc:
        logger.warning(f"Could not create backup file: {exc}")

def atomic_write_json(path: Path, data: dict):
    """Write JSON atomically using a temp file."""
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        os.replace(tmp_path, path)
        logger.debug(f"Data saved to {path}")
    except Exception as exc:
        logger.error(f"Failed to write {path}: {exc}")
        if tmp_path.exists():
            tmp_path.unlink()
        raise

def load_data() -> dict:
    """Load data from file into memory cache."""
    global _DATA_CACHE

    if _DATA_CACHE is not None:
        return _DATA_CACHE

    if not CONFIG["data_file"].exists():
        logger.info("Creating new data file")
        _DATA_CACHE = default_schema()
        return _DATA_CACHE

    try:
        with open(CONFIG["data_file"], "r", encoding="utf-8") as f:
            data = json.load(f)
            logger.info("Data loaded successfully")
    except json.JSONDecodeError as exc:
        logger.error(f"Corrupted data file: {exc}")
        backup_file(CONFIG["data_file"], CONFIG["backup_file"])
        _DATA_CACHE = default_schema()
        return _DATA_CACHE
    except OSError as exc:
        logger.error(f"Could not read data file: {exc}")
        _DATA_CACHE = default_schema()
        return _DATA_CACHE

    _DATA_CACHE = ensure_schema(data)
    return _DATA_CACHE

def save_data(data: Optional[dict] = None):
    """Synchronous save (fallback)."""
    global _DATA_CACHE

    if data is not None:
        _DATA_CACHE = data

    if _DATA_CACHE is None:
        return

    try:
        backup_file(CONFIG["data_file"], CONFIG["backup_file"])
        atomic_write_json(CONFIG["data_file"], _DATA_CACHE)
    except Exception as exc:
        logger.error(f"save_data failed: {exc}")

async def save_data_async(data: Optional[dict] = None):
    """Async save with lock for safety."""
    global _DATA_CACHE

    if data is not None:
        _DATA_CACHE = data

    if _DATA_CACHE is None:
        return

    async with _DATA_LOCK:
        try:
            _DATA_CACHE["last_updated"] = datetime.now().isoformat()
            backup_file(CONFIG["data_file"], CONFIG["backup_file"])
            atomic_write_json(CONFIG["data_file"], _DATA_CACHE)
        except Exception as exc:
            logger.error(f"save_data_async failed: {exc}")

def prune_message_archive(data: dict) -> dict:
    """Prune message archive to max size."""
    if len(data["message_archive"]) > CONFIG["max_message_archive"]:
        removed = len(data["message_archive"]) - CONFIG["max_message_archive"]
        data["message_archive"] = data["message_archive"][-CONFIG["max_message_archive"]:]
        logger.info(f"Pruned {removed} old messages from archive")
    return data

def clean_token(token: str) -> str:
    """Clean and validate a token."""
    if any(blacklisted in token for blacklisted in WORD_BLACKLIST):
        return ""
    return token.strip(".,!?\"()[]{}*<>~`").lower()

def learn_sentence_trigrams(data: dict, text: str, user_id: Optional[int] = None):
    """Learn trigrams from text."""
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

    user_id_str = str(user_id) if user_id else None

    _append_trigram(data, "__start__ __start__", tokens[0], user_id_str)
    _append_trigram(data, f"__start__ {tokens[0]}", tokens[1], user_id_str)

    for i in range(len(tokens) - 2):
        w1, w2, w3 = tokens[i], tokens[i + 1], tokens[i + 2]
        key = f"{w1} {w2}"
        _append_trigram(data, key, w3, user_id_str)

def _append_trigram(data: dict, key: str, value: str, user_id: Optional[str] = None):
    """Append a trigram to the data structure."""
    if key not in data["trigrams"]:
        data["trigrams"][key] = []
    data["trigrams"][key].append(value)

    if user_id:
        if user_id not in data["user_trigrams"]:
            data["user_trigrams"][user_id] = {}
        if key not in data["user_trigrams"][user_id]:
            data["user_trigrams"][user_id][key] = []
        data["user_trigrams"][user_id][key].append(value)

def generate_complex_ai_mimic(data: dict, user_id: Optional[int] = None, seed_word: Optional[str] = None, max_words: int = 20) -> str:
    """Generate AI-mimicked text using trigrams."""
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

# ============================================================
# Background Tasks
# ============================================================
@tasks.loop(minutes=5)
async def auto_save_task():
    """Save data periodically."""
    try:
        data = load_data()
        data = prune_message_archive(data)
        await save_data_async(data)
    except Exception as exc:
        logger.error(f"Auto-save task failed: {exc}")

@tasks.loop(minutes=10)
async def status_rotator():
    """Update bot status."""
    try:
        data = load_data()
        total_connections = sum(len(v) for v in data["trigrams"].values())
        status_text = f"🧠 Processing {total_connections} layers | /help"
        await bot.change_presence(activity=discord.CustomActivity(name=status_text))
    except Exception as exc:
        logger.error(f"Status rotator failed: {exc}")

# ============================================================
# Bot Events
# ============================================================
@bot.event
async def on_ready():
    """Bot is ready."""
    logger.info(f"✅ Bot online: {bot.user.name} ({bot.user.id})")

    # Sync commands
    guild = None
    if CONFIG["guild_id"]:
        try:
            guild = bot.get_guild(int(CONFIG["guild_id"]))
            if guild:
                bot.tree.copy_global_to(guild=guild)
                await bot.tree.sync(guild=guild)
                logger.info(f"✅ Commands synced to guild {guild.id}")
            else:
                logger.warning(f"Guild {CONFIG['guild_id']} not found, syncing globally")
                await bot.tree.sync()
        except (TypeError, ValueError) as exc:
            logger.error(f"Invalid GUILD_ID: {exc}")
            await bot.tree.sync()
    else:
        try:
            await bot.tree.sync()
            logger.info("✅ Commands synced globally")
        except Exception as exc:
            logger.error(f"Failed to sync commands: {exc}")

    # Start background tasks
    if not status_rotator.is_running():
        status_rotator.start()
        logger.info("🔄 Status rotator started")

    if not auto_save_task.is_running():
        auto_save_task.start()
        logger.info("💾 Auto-save task started")

    # Preload data
    load_data()

@bot.event
async def on_message(message: discord.Message):
    """Process incoming messages."""
    if message.author.bot:
        return

    if message.content.startswith("!"):
        await bot.process_commands(message)
        return

    data = load_data()
    user_id = str(message.author.id)

    # Track user activity
    data["user_chat_counts"][user_id] = data["user_chat_counts"].get(user_id, 0) + 1

    # Archive message
    if message.content.strip():
        data["message_archive"].append({
            "content": message.content,
            "author": message.author.display_name,
            "user_id": user_id,
            "channel": message.channel.name,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        })

    # Learn from message
    learn_sentence_trigrams(data, message.content, message.author.id)
    prune_message_archive(data)

    # Optional: Random responses (only if enabled)
    if CONFIG["enable_random_responses"]:
        channel_key = str(message.channel.id)
        now = datetime.now()
        last_reply = _LAST_RANDOM_REPLY.get(channel_key)

        if last_reply is None or (now - last_reply).total_seconds() >= 60:
            if len(message.content) > 25 and random.random() < CONFIG["random_reply_chance"]:
                if not any(q["text"] == message.content for q in data["quotes"]):
                    data["quotes"].append({
                        "text": message.content,
                        "added_by": f"{message.author.display_name} (Auto-Captured 🤖)",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                    })
                    await message.add_reaction("👑")

            if random.random() < CONFIG["random_reply_chance"] and len(data["trigrams"]) > 25:
                async with message.channel.typing():
                    await asyncio.sleep(random.uniform(0.6, 1.8))
                    potential_seeds = [w for w in message.content.split() if len(w) > 3]
                    seed = random.choice(potential_seeds) if potential_seeds else None
                    target = random.choice([None, user_id])
                    reply = generate_complex_ai_mimic(data, user_id=target, seed_word=seed)
                    await message.channel.send(reply)
                    _LAST_RANDOM_REPLY[channel_key] = now

    await bot.process_commands(message)
    await save_data_async(data)

@bot.event
async def on_error(event, *args, **kwargs):
    """Handle bot errors."""
    logger.exception(f"Error in {event}")

# ============================================================
# Commands
# ============================================================
@bot.hybrid_command(name="help", description="View all available commands")
async def help_command(ctx: commands.Context):
    """Display help."""
    embed = discord.Embed(
        title="👑 LoreKeeper — Command Matrix",
        description="Use slash commands (`/`) or prefix (`!`)",
        color=discord.Color.gold()
    )

    for cmd in sorted(bot.tree.get_commands(), key=lambda c: c.name):
        embed.add_field(name=f"/{cmd.name}", value=cmd.description or "No description", inline=False)

    embed.set_footer(text="LoreKeeper v5.0 • Production Ready")
    await ctx.reply(embed=embed, ephemeral=bool(ctx.interaction))

@bot.hybrid_command(name="mimic", description="Generate an AI response")
@commands.cooldown(1, CONFIG["command_cooldown"], commands.BucketType.user)
async def mimic(ctx: commands.Context):
    """Generate mimicked text."""
    data = load_data()
    reply = generate_complex_ai_mimic(data, user_id=ctx.author.id)
    await ctx.reply(reply, ephemeral=bool(ctx.interaction))

@bot.hybrid_command(name="stats", description="View neural matrix statistics")
async def stats(ctx: commands.Context):
    """Show statistics."""
    data = load_data()
    embed = discord.Embed(title="🧠 Neural Matrix Stats", color=discord.Color.blurple())
    embed.add_field(name="Trigram Connections", value=f"{sum(len(v) for v in data['trigrams'].values()):,}", inline=True)
    embed.add_field(name="Captured Quotes", value=f"{len(data['quotes']):,}", inline=True)
    embed.add_field(name="Archived Messages", value=f"{len(data['message_archive']):,}", inline=True)
    embed.add_field(name="Tracked Users", value=f"{len(data['user_chat_counts']):,}\", inline=True)
    await ctx.reply(embed=embed, ephemeral=bool(ctx.interaction))

@bot.hybrid_command(name="brainscan", description="Scan recent server history")
@commands.has_permissions(administrator=True)
@commands.cooldown(1, 300, commands.BucketType.user)
async def brainscan(ctx: commands.Context):
    """Scan server history for learning."""
    data = load_data()

    if ctx.interaction:
        await ctx.defer(ephemeral=True)
        await ctx.followup.send("🧠⚡ Scanning recent server history... (this may take a minute)", ephemeral=True)
    else:
        await ctx.send("🧠⚡ Scanning recent server history... (this may take a minute)")

    cutoff = datetime.now() - timedelta(days=CONFIG["history_days"])
    scanned_count = 0
    scanned_channels = 0

    try:
        for channel in ctx.guild.text_channels[:CONFIG["max_scan_channels"]]:
            if scanned_channels >= CONFIG["max_scan_channels"]:
                break

            try:
                scanned_channels += 1
                logger.info(f"Scanning channel: {channel.name}")
                
                async for msg in channel.history(limit=CONFIG["max_scan_messages"], after=cutoff):
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
                    
                    await asyncio.sleep(0.01)
                    
            except Exception as exc:
                logger.warning(f"Error scanning {channel.name}: {exc}")
                continue

        data = prune_message_archive(data)
        await save_data_async(data)

        msg_str = f"🧠⚡ **BrainScan Complete!** Indexed **{scanned_count:,}** messages from **{scanned_channels}** channels."
        logger.info(f"BrainScan finished: {scanned_count} messages from {scanned_channels} channels")
        
        if ctx.interaction:
            await ctx.followup.send(msg_str, ephemeral=True)
        else:
            await ctx.send(msg_str)
            
    except Exception as exc:
        logger.error(f"BrainScan failed: {exc}")
        error_msg = f"❌ BrainScan failed: {str(exc)}"
        if ctx.interaction:
            await ctx.followup.send(error_msg, ephemeral=True)
        else:
            await ctx.send(error_msg)

@bot.hybrid_command(name="quote", description="Get a random server quote")
async def quote(ctx: commands.Context):
    """Pull a quote."""
    data = load_data()
    if not data["quotes"]:
        return await ctx.reply("❌ No quotes captured yet!", ephemeral=bool(ctx.interaction))
    
    q = random.choice(data["quotes"])
    embed = discord.Embed(title="👑 Legendary Quote", description=f"\"{q['text']}\"", color=discord.Color.gold())
    embed.set_footer(text=f"Added by: {q['added_by']} | {q['timestamp']}")
    await ctx.reply(embed=embed, ephemeral=bool(ctx.interaction))

@bot.hybrid_command(name="addquote", description="Add a quote to server lore")
@commands.cooldown(1, 10, commands.BucketType.user)
async def addquote(ctx: commands.Context, *, text: str):
    """Add a quote."""
    if len(text) > 1000:
        return await ctx.reply("❌ Quote too long (max 1000 chars)", ephemeral=bool(ctx.interaction))
    
    data = load_data()
    data["quotes"].append({
        "text": text,
        "added_by": f"{ctx.author.display_name} (Manual ✨)",
        "timestamp": datetime.now*
