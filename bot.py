import discord
from discord.ext import commands
import json
import random
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables securely from .env
load_dotenv()

# Setup explicit intents (Message Content + Reactions are required)
intents = discord.Intents.default()
intents.message_content = True
intents.guild_messages = True
intents.guild_message_reactions = True

# Disable default help so we can use our own custom one
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
    print(f"✨ Ultimate LoreBot Online: {bot.user.name} (ID: {bot.user.id})")
    print("------------------------------------------------------")
    await bot.change_presence(activity=discord.Game(name="Managing Server Lore | !help"))

# --- 0. CUSTOM HELP COMMAND ---

@bot.command(name="help")
async def custom_help(ctx):
    """Shows a list of all available commands and how to use them."""
    embed = discord.Embed(
        title="📜 Server LoreBot - Command Guide",
        description="Here are all the commands you can use to manage our inside jokes and history:",
        color=discord.Color.purple()
    )

    embed.add_field(
        name="💬 Quote Commands",
        value=(
            "`!quote <text>` - Manually save an iconic quote.\n"
            "`!randomquote` - Pull a random quote (with a roll button!)\n"
            "`!listquotes` - View a list of recently saved quotes."
        ),
        inline=False
    )

    embed.add_field(
        name="📚 Lore & Inside Jokes",
        value=(
            "`!define <term> <explanation>` - Document server slang/lore.\n"
            "`!lookup <term>` - Look up a specific piece of lore.\n"
            "`!listlore` - View all documented lore keywords."
        ),
        inline=False
    )

    embed.add_field(
        name="🔍 Search & Fun Features",
        value=(
            "`!searchmsg <keyword>` - Scan past chat history for a word.\n"
            "`!lorestats` - View the leaderboard of top server historians.\n"
            "🔖 **Reaction Feature:** React to *any* old message with a bookmark emoji to save it instantly!"
        ),
        inline=False
    )

    embed.set_footer(text="Type any command with the '!' prefix to get started!")
    await ctx.send(embed=embed)

# --- 1. QUOTE SYSTEM WITH INTERACTIVE BUTTON ---

class QuoteView(discord.ui.View):
    """Adds an interactive button to roll another random quote."""
    def __init__(self):
        super().__init__(timeout=180) # Button expires after 3 minutes

    @discord.ui.button(label="Roll Another Quote", style=discord.ButtonStyle.blurple, emoji="🔄")
    async def roll_again(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        quotes = data.get("quotes", [])
        if not quotes:
            return await interaction.response.send_message("📭 The archive is empty!", ephemeral=True)
        
        chosen = random.choice(quotes)
        embed = discord.Embed(
            description=f"💬 \"{chosen['text']}\"",
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Added by {chosen['added_by']} in #{chosen['channel']} • {chosen['timestamp']}")
        await interaction.response.edit_message(embed=embed, view=self)

@bot.command(name="quote")
async def add_quote(ctx, *, quote_text: str = None):
    """Archives an iconic quote. Usage: !quote <text>"""
    if not quote_text:
        await ctx.send("❌ **Error:** Please provide a quote! Example: `!quote 'Never give up' - Someone`")
        return

    data = load_data()
    new_entry = {
        "text": quote_text,
        "added_by": ctx.author.display_name,
        "channel": ctx.channel.name,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    data["quotes"].append(new_entry)
    save_data(data)
    
    embed = discord.Embed(
        title="📥 Quote Archived Successfully",
        description=f"*{quote_text}*",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Logged by {ctx.author.display_name}")
    await ctx.send(embed=embed)

@bot.command(name="randomquote")
async def random_quote(ctx):
    """Pulls a random quote with an interactive roll button."""
    data = load_data()
    quotes = data.get("quotes", [])
    
    if not quotes:
        await ctx.send("📭 The archive is completely empty! Add some using `!quote`.")
        return
        
    chosen = random.choice(quotes)
    embed = discord.Embed(
        description=f"💬 \"{chosen['text']}\"",
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"Added by {chosen['added_by']} in #{chosen['channel']} • {chosen['timestamp']}")
    
    await ctx.send(embed=embed, view=QuoteView())

@bot.command(name="listquotes")
async def list_quotes(ctx):
    """Shows a summary list of saved quotes."""
    data = load_data()
    quotes = data.get("quotes", [])
    if not quotes:
        return await ctx.send("📭 No quotes saved yet! Use `!quote` or react with 🔖.")
    
    quote_lines = []
    for i, q in enumerate(quotes[-15:], start=1):
        quote_text_snippet = (q['text'][:45] + '...') if len(q['text']) > 45 else q['text']
        quote_lines.append(f"**{i}.** \"{quote_text_snippet}\" — *{q['added_by']}*")
    
    embed = discord.Embed(
        title="💬 Saved Quotes Archive",
        description="\n".join(quote_lines),
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"Showing recent quotes (Total saved: {len(quotes)})")
    await ctx.send(embed=embed)

# --- 2. LORE & INSIDE JOKE SYSTEM ---

@bot.command(name="define")
async def define_lore(ctx, term: str = None, *, explanation: str = None):
    """Documents server slang/lore. Usage: !define <term> <backstory>"""
    if not term or not explanation:
        await ctx.send("❌ **Error:** Missing arguments. Use: `!define [term] [explanation]`")
        return
        
    data = load_data()
    term_lower = term.lower()
    
    data["lore"][term_lower] = {
        "original_term": term,
        "explanation": explanation,
        "defined_by": ctx.author.display_name
    }
    save_data(data)
    
    await ctx.send(f"📚 **Lore Documented:** '{term}' is now permanently recorded in server history.")

@bot.command(name="lookup")
async def lookup_lore(ctx, *, term: str = None):
    """Looks up a piece of lore. Usage: !lookup <term>"""
    if not term:
        await ctx.send("❌ **Error:** Please specify what term you want to look up.")
        return
        
    data = load_data()
    term_lower = term.lower()
    
    if term_lower not in data["lore"]:
        await ctx.send(f"🔍 No lore entry found for **'{term}'**. Try adding it with `!define`!")
        return
        
    item = data["lore"][term_lower]
    embed = discord.Embed(
        title=f"📜 Lore Entry: {item['original_term']}",
        description=item["explanation"],
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Documented by {item['defined_by']}")
    await ctx.send(embed=embed)

@bot.command(name="listlore")
async def list_lore(ctx):
    """Lists all documented lore terms and inside jokes."""
    data = load_data()
    lore = data.get("lore", {})
    if not lore:
        return await ctx.send("📚 No lore terms documented yet! Use `!define` to add some.")
    
    terms = [item['original_term'] for item in lore.values()]
    embed = discord.Embed(
        title="📚 All Server Lore & Inside Jokes",
        description=", ".join(terms),
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Total lore entries: {len(terms)}")
    await ctx.send(embed=embed)

# --- 3. MESSAGE HISTORY SEARCH ---

@bot.command(name="searchmsg")
async def search_messages(ctx, *, keyword: str = None):
    """Scans past channel history for a specific keyword."""
    if not keyword:
        await ctx.send("❌ Please provide a keyword to search for! Example: `!searchmsg pizza`")
        return

    searching_msg = await ctx.send(f"🔍 Scanning recent message history for '**{keyword}**'...")
    found_count = 0
    
    async for message in ctx.channel.history(limit=150):
        if keyword.lower() in message.content.lower() and not message.author.bot:
            embed = discord.Embed(
                description=f"*{message.content}*",
                color=discord.Color.purple()
            )
            embed.set_footer(text=f"Found from {message.author.display_name} in #{message.channel.name} • {message.created_at.strftime('%Y-%m-%d')}")
            await ctx.send(embed=embed)
            found_count += 1
            if found_count >= 3:
                break

    await searching_msg.delete()
    if found_count == 0:
        await ctx.send(f"📭 No messages containing '**{keyword}**' were found in recent history.")

# --- 4. LEADERBOARD STATS ---

@bot.command(name="lorestats")
async def lore_stats(ctx):
    """Shows who has contributed the most quotes and lore to the server."""
    data = load_data()
    quotes = data.get("quotes", [])
    lore = data.get("lore", {})

    contributors = {}

    for q in quotes:
        user = q.get("added_by", "Unknown")
        contributors[user] = contributors.get(user, 0) + 1

    for l_key, l_val in lore.items():
        user = l_val.get("defined_by", "Unknown")
        contributors[user] = contributors.get(user, 0) + 1

    if not contributors:
        return await ctx.send("📊 No contributions recorded yet!")

    sorted_contributors = sorted(contributors.items(), key=lambda x: x[1], reverse=True)

    embed = discord.Embed(
        title="🏆 Server Historians Leaderboard",
        description="The top contributors to our inside jokes and lore:",
        color=discord.Color.orange()
    )

    for i, (user, count) in enumerate(sorted_contributors[:5], start=1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📌"
        embed.add_field(name=f"{medal} Rank {i}: {user}", value=f"**{count}** contributions", inline=False)

    await ctx.send(embed=embed)

# --- 5. REACTION-TO-SAVE (STARBOARD) ---

@bot.event
async def on_reaction_add(reaction, user):
    """Automatically saves a message as a quote if anyone reacts with a bookmark 🔖 emoji."""
    if user.bot:
        return

    if str(reaction.emoji) == "🔖":
        message = reaction.message
        if not message.content:
            return

        data = load_data()
        
        existing_texts = [q["text"] for q in data["quotes"]]
        if message.content in existing_texts:
            return

        new_entry = {
            "text": message.content,
            "added_by": message.author.display_name,
            "channel": message.channel.name if message.channel else "unknown",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        }

        data["quotes"].append(new_entry)
        save_data(data)

        try:
            embed = discord.Embed(
                title="🔖 Auto-Archived via Reaction!",
                description=f"*{message.content}*",
                color=discord.Color.teal()
            )
            embed.set_footer(text=f"Originally said by {message.author.display_name} • Saved via reaction by {user.display_name}")
            await message.channel.send(embed=embed)
        except Exception as e:
            print(f"Error sending auto-archive message: {e}")

# Run the bot securely
BOT_TOKEN = os.getenv("DISCORD_TOKEN")

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ Error: DISCORD_TOKEN not found in environment variables or .env file.")
    else:
        bot.run(BOT_TOKEN)