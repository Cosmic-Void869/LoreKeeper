import os
import json
import random
from datetime import datetime
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables securely
load_dotenv()

# Setup minimal intents (Message Content is required for reading messages)
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
DATA_FILE = "server_lore.json"

def load_data():
    """Safely loads database file or returns fallback schema."""
    if not os.path.exists(DATA_FILE):
        return {"quotes": [], "lore": {}}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {"quotes": [], "lore": {}}

def save_data(data):
    """Saves current state safely to disk."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

@bot.event
async def on_ready():
    print(f"✨ LoreBot Online: {bot.user.name} (ID: {bot.user.id})")

# --- 1. HELP COMMAND ---
@bot.command(name="help")
async def custom_help(ctx):
    """Shows all available commands."""
    embed = discord.Embed(
        title="📜 LoreBot Commands",
        description="Here are the essential commands:",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="💬 Quotes",
        value="`!quote <text>` - Save a quote\n`!randomquote` - Show a random quote",
        inline=False
    )
    embed.add_field(
        name="📚 Lore",
        value="`!define <term> <text>` - Save inside joke/lore\n`!lookup <term>` - Look up lore",
        inline=False
    )
    embed.add_field(
        name="🔍 Search",
        value="`!searchmsg <keyword>` - Scan recent chat history for a word",
        inline=False
    )
    await ctx.send(embed=embed)

# --- 2. QUOTE SYSTEM ---
@bot.command(name="quote")
async def add_quote(ctx, *, quote_text: str = None):
    """Saves a quote."""
    if not quote_text:
        return await ctx.send("❌ **Error:** Please provide quote text! Example: `!quote Hello there`")
    
    data = load_data()
    data["quotes"].append({
        "text": quote_text,
        "added_by": ctx.author.display_name,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    save_data(data)
    await ctx.send("✅ Quote saved successfully!")

@bot.command(name="randomquote")
async def random_quote(ctx):
    """Pulls a random quote."""
    data = load_data()
    quotes = data.get("quotes", [])
    if not quotes:
        return await ctx.send("📭 The archive is completely empty! Add some using `!quote`.")
    
    chosen = random.choice(quotes)
    embed = discord.Embed(description=f"💬 \"{chosen['text']}\"", color=discord.Color.gold())
    embed.set_footer(text=f"Added by {chosen['added_by']} • {chosen['timestamp']}")
    await ctx.send(embed=embed)

# --- 3. LORE SYSTEM ---
@bot.command(name="define")
async def define_lore(ctx, term: str = None, *, explanation: str = None):
    """Saves a lore term."""
    if not term or not explanation:
        return await ctx.send("❌ **Error:** Use `!define <term> <explanation>`")
    
    data = load_data()
    data["lore"][term.lower()] = {
        "original_term": term,
        "explanation": explanation,
        "defined_by": ctx.author.display_name
    }
    save_data(data)
    await ctx.send(f"📚 Lore documented for **'{term}'**!")

@bot.command(name="lookup")
async def lookup_lore(ctx, *, term: str = None):
    """Looks up a lore term."""
    if not term:
        return await ctx.send("❌ **Error:** Please specify what term to look up.")
    
    data = load_data()
    item = data["lore"].get(term.lower())
    if not item:
        return await ctx.send(f"🔍 No lore entry found for **'{term}'**.")
    
    embed = discord.Embed(title=f"📜 {item['original_term']}", description=item["explanation"], color=discord.Color.blue())
    embed.set_footer(text=f"Defined by {item['defined_by']}")
    await ctx.send(embed=embed)

# --- 4. SAFE MESSAGE HISTORY SEARCH ---
@bot.command(name="searchmsg")
async def search_messages(ctx, *, keyword: str = None):
    """Scans recent channel history safely for a specific keyword."""
    if not keyword:
        return await ctx.send("❌ Please provide a keyword to search for! Example: `!searchmsg pizza`")

    searching_msg = await ctx.send(f"🔍 Scanning recent message history for '**{keyword}**'...")
    found_count = 0
    
    try:
        async for message in ctx.channel.history(limit=100):
            if keyword.lower() in message.content.lower() and not message.author.bot:
                embed = discord.Embed(
                    description=f"*{message.content}*",
                    color=discord.Color.purple()
                )
                embed.set_footer(text=f"Found from {message.author.display_name} • {message.created_at.strftime('%Y-%m-%d')}")
                await ctx.send(embed=embed)
                found_count += 1
                if found_count >= 3:  # Limits results to avoid spamming the channel
                    break
    except discord.Forbidden:
        await searching_msg.delete()
        return await ctx.send("❌ **Error:** I don't have permission to read message history in this channel!")
    except Exception as e:
        print(f"Search error: {e}")

    await searching_msg.delete()
    if found_count == 0:
        await ctx.send(f"📭 No messages containing '**{keyword}**' were found in recent history.")

# --- RUN BOT ---
BOT_TOKEN = os.getenv("DISCORD_TOKEN")

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ Error: DISCORD_TOKEN missing in your .env file.")
    else:
        bot.run(BOT_TOKEN)