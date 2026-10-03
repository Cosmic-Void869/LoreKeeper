import discord
from discord.ext import commands
import json
import random
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()

# Setup bot permissions (Intents)
intents = discord.Intents.default()
intents.message_content = True  # Required to read command text

# Set your command prefix (e.g., !quote, !lookup)
bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "server_lore.json"

def load_data():
    """Loads the database file, or creates an empty structure if missing."""
    if not os.path.exists(DATA_FILE):
        return {"quotes": [], "lore": {}}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {"quotes": [], "lore": {}}

def save_data(data):
    """Saves the current data state back to the JSON file."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

@bot.event
async def on_ready():
    print(f"✨ Success! Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("------------------------------------------------------")
    # Set a custom playing status
    await bot.change_presence(activity=discord.Game(name="with deep server lore | !help"))

@bot.command(name="quote")
async def add_quote(ctx, *, quote_text: str = None):
    """Saves an iconic quote to the database. Usage: !quote She actually said that!"""
    if not quote_text:
        await ctx.send("❌ **Error:** Please provide a quote! Example: `!quote \"I am the smartest person alive\" - John`")
        return

    data = load_data()
    
    # Structure the new quote entry
    new_quote = {
        "text": quote_text,
        "added_by": ctx.author.display_name,
        "channel": ctx.channel.name,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    data["quotes"].append(new_quote)
    save_data(data)
    
    await ctx.send(f"✅ **Archived!** That legendary line has been locked away safely in the history books.")

@bot.command(name="randomquote")
async def random_quote(ctx):
    """Pulls a random masterpiece from your archive. Usage: !randomquote"""
    data = load_data()
    quotes = data.get("quotes", [])
    
    if not quotes:
        await ctx.send("📭 The archive is completely empty. Start saving history using `!quote <text>`!")
        return
        
    chosen = random.choice(quotes)
    
    # Create a stylized card layout (Embed)
    embed = discord.Embed(
        description=f"*{chosen['text']}*", 
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"Logged by {chosen['added_by']} in #{chosen['channel']} • {chosen['timestamp']}")
    
    await ctx.send(embed=embed)

@bot.command(name="define")
async def define_lore(ctx, term: str = None, *, explanation: str = None):
    """Adds a definition for server slang/inside joke. Usage: !define spooning Stealing spoons from the kitchen"""
    if not term or not explanation:
        await ctx.send("❌ **Error:** Missing arguments. Use: `!define [word/phrase] [the backstory/explanation]`")
        return
        
    data = load_data()
    term_lower = term.lower()
    
    data["lore"][term_lower] = {
        "original_term": term,
        "explanation": explanation,
        "defined_by": ctx.author.display_name
    }
    save_data(data)
    
    await ctx.send(f"📚 **Lore Documented:** '{term}' is now part of official server history.")

@bot.command(name="lookup")
async def lookup_lore(ctx, *, term: str = None):
    """Looks up a documented inside joke or phrase. Usage: !lookup spooning"""
    if not term:
        await ctx.send("❌ **Error:** What term do you want to look up? Example: `!lookup spooning``")
        return
        
    data = load_data()
    term_lower = term.lower()
    
    if term_lower not in data["lore"]:
        await ctx.send(f"🔍 I couldn't find any server lore matching **'{term}'**. Try registering it with `!define`!")
        return
        
    lore_item = data["lore"][term_lower]
    
    embed = discord.Embed(
        title=f"📜 Lore Entry: {lore_item['original_term']}",
        description=lore_item["explanation"],
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Documented by {lore_item['defined_by']}")
    
    await ctx.send(embed=embed)

# 🔐 Pulls token securely from environment variables
BOT_TOKEN = os.getenv("DISCORD_TOKEN")

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ Error: 'DISCORD_TOKEN' environment variable not found! Make sure your .env file is set up.")
    else:
        bot.run(BOT_TOKEN)
