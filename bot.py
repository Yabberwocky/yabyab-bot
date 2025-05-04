```python
import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import datetime
import os

Load token from environment or paste directly for quick testing
TOKEN = os.getenv("DISCORD_TOKEN") or "YOUR_BOT_TOKEN_HERE"

Discord settings
IMAGE_CHANNEL_ID = 1359782718426316840  # Channel to post images
DAILY_ROLE_ID = 1368237860326473859     # Role to assign on image upload
TEMP_ROLE_ID = 1368238029571100834      # Temporary role for /takebraincells

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Failed to sync commands: {e}')
    daily_role_removal.start()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id == IMAGE_CHANNEL_ID and message.attachments:
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith('image'):
                role = message.guild.get_role(DAILY_ROLE_ID)
                if role and role not in message.author.roles:
                    await message.author.add_roles(role)
                    print(f"Assigned role to {message.author}")
                break
    await bot.process_commands(message)

@tasks.loop(time=datetime.time(hour=23, minute=59))
async def daily_role_removal():
    for guild in bot.guilds:
        role = guild.get_role(DAILY_ROLE_ID)
        if role:
            for member in role.members:
                await member.remove_roles(role)
                print(f"Removed role from {member}")

@bot.tree.command(name="takebraincells", description="Give a role to someone for 5 minutes.")
@app_commands.describe(user="User to give temporary braincell role to")
async def takebraincells(interaction: discord.Interaction, user: discord.Member):
    executor = interaction.user
    guild = interaction.guild

    required_role = guild.get_role(DAILY_ROLE_ID)
if required_role not in executor.roles:
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return

    temp_role = guild.get_role(TEMP_ROLE_ID)
    if temp_role:
        await user.add_roles(temp_role)
        await interaction.response.send_message(
            f"{user.mention} has received the braincell role for 5 minutes."
        )
        await asyncio.sleep(300)
        await user.remove_roles(temp_role)
        print(f"Removed temporary role from {user}")
    else:
        await interaction.response.send_message("Temporary role not found.", ephemeral=True)
        @bot.event
async def on_message(message):
    if message.author.bot:
        return

    temp_role_id = 1368238029571100834
    if any(role.id == temp_role_id for role in message.author.roles):
        response = await message.channel.send(f"{message.author.mention} shut up dumb fuck")
        await asyncio.sleep(5)
        await response.delete()

    await bot.process_commands(message)

bot.run(TOKEN)
```
