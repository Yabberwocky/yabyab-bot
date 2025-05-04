import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import datetime
import os

# Load token from environment - REMOVE OR COMMENT OUT "YOUR_BOT_TOKEN_HERE" BEFORE DEPLOYING
TOKEN = os.getenv("DISCORD_TOKEN") # or "YOUR_BOT_TOKEN_HERE"

# Discord settings
IMAGE_CHANNEL_ID = 1359782718426316840  # Channel to post images
DAILY_ROLE_ID = 1368237860326473859    # Role to assign on image upload
TEMP_ROLE_ID = 1368238029571100834     # Temporary role for /takebraincells

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to store the time when a user received the daily role
user_daily_role_times = {}

# List of image MIME types to check
IMAGE_MIME_TYPES = [
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/bmp',
    'image/webp',
    'image/tiff',
    'image/heic',  # Add HEIC support
    'image/heif',  # Add HEIF support
]


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Failed to sync commands: {e}')
    daily_role_removal_task.start()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Logic for assigning role on image upload
    if message.channel.id == IMAGE_CHANNEL_ID and message.attachments:
        for attachment in message.attachments:
            if attachment.content_type in IMAGE_MIME_TYPES:
                guild = message.guild
                user = message.author
                role = guild.get_role(DAILY_ROLE_ID)
                if role and role not in user.roles:
                    await user.add_roles(role)
                    now = datetime.datetime.now(datetime.timezone.utc)
                    user_daily_role_times[user.id] = now
                    print(f"Assigned role to {user} at {now}")
                break
    await bot.process_commands(message)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Logic for replying to users with the temporary role
    temp_role_id = 1368238029571100834
    if any(role.id == temp_role_id for role in message.author.roles):
        response = await message.channel.send(f"{message.author.mention} shut up dumb fuck")
        await asyncio.sleep(5)
        await response.delete()

    await bot.process_commands(message)

@tasks.loop(seconds=60) # Check every minute
async def daily_role_removal_task():
    now = datetime.datetime.now(datetime.timezone.utc)
    guilds = bot.guilds
    daily_role_id = DAILY_ROLE_ID

    users_to_remove = []
    for user_id, assigned_time in list(user_daily_role_times.items()):
        if now - assigned_time >= datetime.timedelta(hours=12):
            users_to_remove.append(user_id)
            del user_daily_role_times[user_id]

    for guild in guilds:
        role = guild.get_role(daily_role_id)
        if role:
            for user_id in users_to_remove:
                member = guild.get_member(user_id)
                if member and role in member.roles:
                    await member.remove_roles(role)
                    print(f"Removed daily role from {member} (after 12 hours)")

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

bot.run(TOKEN)

