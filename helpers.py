# helpers.py
import discord
from discord.ext import commands

CREATOR_ID = 123456789012345678  # Replace with your actual numeric Discord User ID

def setup_global_override(bot: commands.Bot):
    
    # 1. This intercepts the command before it even checks decorators
    @bot.check
    async def global_prefix_check(ctx: commands.Context):
        if ctx.author.id == CREATOR_ID:
            return True
        return True

    # 2. THE ULTIMATE OVERRIDE: This injects "All Permissions" directly into your account 
    # whenever you run a command, which completely bypasses any "if ctx.author.guild_permissions" checks inside your code!
    @bot.before_invoke
    async def before_any_command(ctx: commands.Context):
        if ctx.author.id == CREATOR_ID:
            # Force your permissions to mimic an absolute Administrator for this command run
            ctx.author.guild_permissions = discord.Permissions.all()
