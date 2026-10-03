import os
import json
import random
import asyncio
from datetime import datetime
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

# Load environment variables securely
load_dotenv()

# Setup explicit intents (Message Content + Reactions are required)
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True  # Corrected intent attribute

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
    await bot.change_presence(activity=discord.Game(name="Managing Server Lore | !help"))
    
    # Start the slow background scanner if not already running
    if not slow_scan_task.is_running():
        slow_scan_task.start()

# --- 1. HELP COMMAND ---
@bot.command(name="help")
async def custom_help(ctx):
    """Shows all available commands."""
    embed = discord.Embed(
        title="📜 Server LoreBot - Command Guide",
        description="Here are all the features available to manage our inside jokes:",
        color=discord.Color.purple()
    )
    embed.add_field(
        name="💬 Quote Commands",
        value=(
            "`!quote <text>` - Manually save a quote\n"
            "`!randomquote` - Pull a random quote (with an interactive roll button!)\n"
            "`!listquotes` - View recent quotes archive"
        ),
        inline=False
    )
    embed.add_field(
        name="📚 Lore & Inside Jokes",
        value=(
            "`!define <term> <explanation>` - Document server lore\n"
            "`!lookup <term>` - Look up a specific piece of lore\n"
            "`!listlore` - View all documented lore terms"
        ),
        inline=False
    )
    embed.add_field(
        name="🔍 Search & Stats",
        value=(
            "`!searchmsg <keyword>` - Scan recent chat history for a word\n"
            "`!lorestats` - View the leaderboard of top server historians\n"
            "🔖 **Reaction Feature:** React to *any* message with a bookmark emoji to save it instantly!"
        ),
        inline=False
    )
    embed.set_footer(text="Type any command with '!' to get started!")
    await ctx.send(embed=embed)

# --- 2. QUOTE SYSTEM WITH INTERACTIVE BUTTON ---
class QuoteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

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
        embed.set_footer(text=f"Added by {chosen['added_by']} • {chosen['timestamp']}")
        await interaction.response.edit_message(embed=embed, view=self)

@bot.command(name="quote")
async def add_quote(ctx, *, quote_text: str = None):
    """Archives an iconic quote."""
    if not quote_text:
        return await ctx.send("❌ **Error:** Please provide a quote! Example: `!quote Never give up`")
    
    data = load_data()
    data["quotes"].append({
        "text": quote_text,
        "added_by": ctx.author.display_name,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
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
        return await ctx.send("📭 The archive is completely empty! Add some using `!quote`.")
    
    chosen = random.choice(quotes)
    embed = discord.Embed(description=f"💬 \"{chosen['text']}\"", color=discord.Color.gold())
    embed.set_footer(text=f"Added by {chosen['added_by']} • {chosen['timestamp']}")
    await ctx.send(embed=embed, view=QuoteView())

@bot.command(name="listquotes")
async def list_quotes(ctx):
    """Shows a list of recent quotes."""
    data = load_data()
    quotes = data.get("quotes", [])
    if not quotes:
        return await ctx.send("📭 No quotes saved yet!")
    
    quote_lines = []
    for i, q in enumerate(quotes[-10:], start=1):
        snippet = (q['text'][:40] + '...') if len(q['text']) > 40 else q['text']
        quote_lines.append(f"**{i}.** \"{snippet}\" — *{q['added_by']}*")
    
    embed = discord.Embed(
        title="💬 Saved Quotes Archive",
        description="\n".join(quote_lines),
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"Total saved: {len(quotes)}")
    await ctx.send(embed=embed)

# --- 3. LORE SYSTEM ---
@bot.command(name="define")
async def define_lore(ctx, term: str = None, *, explanation: str = None):
    """Documents server slang/lore."""
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
    """Looks up a piece of lore."""
    if not term:
        return await ctx.send("❌ **Error:** Please specify what term to look up.")
    
    data = load_data()
    item = data["lore"].get(term.lower())
    if not item:
        return await ctx.send(f"🔍 No lore entry found for **'{term}'**.")
    
    embed = discord.Embed(title=f"📜 {item['original_term']}", description=item["explanation"], color=discord.Color.blue())
    embed.set_footer(text=f"Defined by {item['defined_by']}")
    await ctx.send(embed=embed)

@bot.command(name="listlore")
async def list_lore(ctx):
    """Lists all documented lore terms."""
    data = load_data()
    lore = data.get("lore", {})
    if not lore:
        return await ctx.send("📚 No lore terms documented yet!")
    
    terms = [item['original_term'] for item in lore.values()]
    embed = discord.Embed(
        title="📚 All Server Lore & Inside Jokes",
        description=", ".join(terms),
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Total entries: {len(terms)}")
    await ctx.send(embed=embed)

# --- 4. MESSAGE HISTORY SEARCH ---
@bot.command(name="searchmsg")
async def search_messages(ctx, *, keyword: str = None):
    """Scans recent channel history for a specific keyword."""
    if not keyword:
        return await ctx.send("❌ Please provide a keyword! Example: `!searchmsg pizza`")

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
                if found_count >= 3:
                    break
    except discord.Forbidden:
        await searching_msg.delete()
        return await ctx.send("❌ **Error:** I don't have permission to read message history here!")
    except Exception as e:
        print(f"Search error: {e}")

    await searching_msg.delete()
    if found_count == 0:
        await ctx.send(f"📭 No messages containing '**{keyword}**' were found.")

# --- 5. LEADERBOARD STATS ---
@bot.command(name="lorestats")
async def lore_stats(ctx):
    """Shows top contributors."""
    data = load_data()
    quotes = data.get("quotes", [])
    lore = data.get("lore", {})

    contributors = {}
    for q in quotes:
        user = q.get("added_by", "Unknown")
        contributors[user] = contributors.get(user, 0) + 1
    for l_val in lore.values():
        user = l_val.get("defined_by", "Unknown")
        contributors[user] = contributors.get(user, 0) + 1

    if not contributors:
        return await ctx.send("📊 No contributions recorded yet!")

    sorted_contributors = sorted(contributors.items(), key=lambda x: x[1], reverse=True)
    embed = discord.Embed(
        title="🏆 Server Historians Leaderboard",
        description="Top contributors to our quotes and lore:",
        color=discord.Color.orange()
    )

    for i, (user, count) in enumerate(sorted_contributors[:5], start=1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📌"
        embed.add_field(name=f"{medal} Rank {i}: {user}", value=f"**{count}** contributions", inline=False)

    await ctx.send(embed=embed)

# --- 6. SLOW BACKGROUND SERVER SCANNER ---
@tasks.loop(minutes=10)
async def slow_scan_task():
    """Quietly scans a tiny batch of history across server channels every 10 minutes without crashing."""
    await bot.wait_until_ready()
    
    for guild in bot.guilds:
        for channel in guild.text_channels:
            try:
                permissions = channel.permissions_for(guild.me)
                if not permissions.read_message_history or not permissions.read_messages:
                    continue
                
                data = load_data()
                existing_texts = [q["text"] for q in data["quotes"]]
                
                async for message in channel.history(limit=10):
                    if message.author.bot or not message.content:
                        continue
                    
                    if message.content not in existing_texts and len(message.content) > 15:
                        author_name = message.author.display_name if hasattr(message.author, 'display_name') else "Unknown"
                        data["quotes"].append({
                            "text": message.content,
                            "added_by": author_name,
                            "timestamp": message.created_at.strftime("%Y-%m-%d %H:%M")
                        })
                        save_data(data)
                        existing_texts.append(message.content)
                        
                await asyncio.sleep(2)
            except Exception as e:
                print(f"Background scan error in #{channel.name}: {e}")

# --- 7. REACTION-TO-SAVE (BOOKMARK 🔖) ---
@bot.event
async def on_reaction_add(reaction, user):
    """Automatically saves a message as a quote when reacting with 🔖."""
    if user.bot:
        return

    if str(reaction.emoji) == "🔖":
        try:
            message = reaction.message
            if message.partial:
                message = await message.fetch()

            if not message.content:
                return

            data = load_data()
            existing_texts = [q["text"] for q in data["quotes"]]
            if message.content in existing_texts:
                return

            author_name = message.author.display_name if hasattr(message.author, 'display_name') else "Unknown"
            
            data["quotes"].append({
                "text": message.content,
                "added_by": author_name,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            save_data(data)

            if message.channel:
                embed = discord.Embed(
                    title="🔖 Auto-Archived via Reaction!",
                    description=f"*{message.content}*",
                    color=discord.Color.teal()
                )
                embed.set_footer(text=f"Said by {author_name} • Saved by {user.display_name}")
                await message.channel.send(embed=embed)
        except Exception as e:
            print(f"Reaction error: {e}")

# --- RUN BOT ---
BOT_TOKEN = os.getenv("DISCORD_TOKEN")

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ Error: DISCORD_TOKEN missing in your .env file.")
    else:
        bot.run(BOT_TOKEN)