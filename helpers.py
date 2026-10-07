# helpers.py
from discord.ext import commands

# 1. Centralized Creator Settings
CREATOR_ID = 1544359425605898305  # Replace with your actual Discord User ID

# 2. The Custom Prefix Decorator
def prefix_creator_override(required_permission: str = "manage_guild"):
    """
    Bypasses permission checks entirely for the bot creator.
    For regular users, it checks if they have the 'required_permission'.
    """
    async def predicate(ctx: commands.Context):
        # THE OVERRIDE: If it's you, let you through instantly
        if ctx.author.id == CREATOR_ID:
            return True
        
        # Dynamic check: Validates whatever permission string you passed in
        user_perms = ctx.author.guild_permissions
        has_perm = getattr(user_perms, required_permission, False)
        
        if not has_perm:
            # Clean up the permission name for a nicer user message (e.g., manage_guild -> Manage Guild)
            friendly_name = required_permission.replace("_", " ").title()
            await ctx.send(f"❌ You need the **{friendly_name}** permission to use this command!")
            return False
            
        return True
        
    return commands.check(predicate)
