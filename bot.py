import discord
from discord.ext import commands, tasks
import asyncio
import datetime
import os

# Load token from environment - IMPORTANT: Ensure this is set correctly in Render
TOKEN = os.getenv("DISCORD_TOKEN")  #  Ensure this is set in Render!

# Discord settings -  Double check these IDs in your Discord server!
IMAGE_CHANNEL_ID = 1359782718426316840
DAILY_ROLE_ID = 1368237860326473859
TEMP_ROLE_ID = 1368238029571100834

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  #  Enable the members intent

bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to store the time when a user received the daily role
user_daily_role_times = {}


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Failed to sync commands: {e}')
        print(f"Error: {e}")  # Print the full error
    daily_role_removal_task.start()



@bot.event
async def on_message(message):
    print(
        f"on_message event triggered. Message from {message.author.name} in {message.channel.name} (Channel ID: {message.channel.id})")  # ADDED

    if message.author.bot:
        print("Message author is a bot, ignoring.")
        return

    # Logic for assigning role on any message in the specified channel
    if message.channel.id == IMAGE_CHANNEL_ID:
        print("Message is in the correct channel.")  # ADDED
        guild = message.guild
        user = message.author
        role = guild.get_role(DAILY_ROLE_ID)
        if role:
            print(f"Found role: {role.name} (Role ID: {role.id})")  # ADDED
            if role not in user.roles:
                print(
                    f"User {user.name} (User ID: {user.id}) does not have the role, adding it.")  # ADDED
                try:
                    await user.add_roles(role)
                    now = datetime.datetime.now(datetime.timezone.utc)
                    user_daily_role_times[user.id] = now
                    print(f"Assigned role {role.name} to {user.name} at {now}")
                except Exception as e:
                    print(f"Error adding role: {e}")  # ADDED
                    print(f"Failed to add role.  Error: {e}") # IMPROVED ERROR
            else:
                print(f"User {user.name} already has the role.")  # ADDED
        else:
            print(f"Role with ID {DAILY_ROLE_ID} not found in guild!")  # ADDED

    # Logic for replying to users with the temporary role
    temp_role_id = 1368238029571100834
    if any(role.id == temp_role_id for role in message.author.roles):
        response = await message.channel.send(f"{message.author.mention} shut up dumb fuck")
        await asyncio.sleep(5)
        await response.delete()

    await bot.process_commands(message)  # Important: Keep this line!




@tasks.loop(seconds=60)
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
