import discord
from discord.ext import commands, tasks
import asyncio
import datetime
import os
import threading
from flask import Flask
import random

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

# --- Flask App (Keep Alive) ---
app = Flask('')

@app.route('/')
def home():
    # This is the response Uptime Robot will see
    return "Discord bot is alive!"

def run_flask():
    """Runs the Flask web server."""
    try:
        # Render sets the PORT environment variable
        port = int(os.environ.get('PORT', 8080)) # Default 8080 for local test
        print(f"Starting Flask keep-alive server on host 0.0.0.0:{port}")
        # Use debug=False for production on Render
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        print(f"Flask keep-alive server failed: {e}")

def keep_alive():
    """Creates and starts the Flask server in a background thread."""
    # daemon=True ensures the thread exits when the main bot process stops
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("Keep-alive thread initiated.")

# --- Brainrot Feature ---
brainrot_active = False
brainrot_words = [
    "skibidi",
    "ohio",
    "sigma",
    "rizz",
    "alpha",
    "andrew tate",
    "gyatt",
    "mr. breast"
]
brainrot_task = None  # Store the task globally

async def stop_brainrot():
    """Stops the brainrot mode and resets the global variable."""
    global brainrot_active
    global brainrot_task
    brainrot_active = False
    brainrot_task = None #clear the task
    print("Brainrot mode stopped.")

@bot.tree.command(name="brainrot", description="Activates brainrot mode for 3 minutes.")
async def brainrot_command(interaction: discord.Interaction):
    """Activates brainrot mode."""
    global brainrot_active
    global brainrot_task

    # Check for the daily role here!
    daily_role = discord.utils.get(interaction.guild.roles, id=DAILY_ROLE_ID)
    if daily_role not in interaction.user.roles:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    if brainrot_active:
        await interaction.response.send_message("Brainrot mode is already active!", ephemeral=True)
        return

    brainrot_active = True
    await interaction.response.send_message("Brainrot mode activated! Prepare for the cringe...")

    # Create a new task and store it in the global variable
    brainrot_task = asyncio.create_task(asyncio.sleep(180)) # 3 minutes = 180 seconds

    # Schedule the task to stop brainrot after 3 minutes
    await asyncio.sleep(180)
    await stop_brainrot()
    await interaction.channel.send("Brainrot mode has ended.") #send message to the channel where the command was used.


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    try:
        # Remove the guild parameter to sync globally
        synced = await bot.tree.sync() # Sync globally
        print(f'Synced {len(synced)} command(s) globally')
    except Exception as e:
        print(f'Failed to sync commands: {e}')
        print(f"Error: {e}")
    daily_role_removal_task.start()



@bot.event
async def on_message(message):
    global brainrot_active
    global brainrot_words

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

    if brainrot_active:
        random_word = random.choice(brainrot_words)
        await message.channel.send(random_word)

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



@bot.tree.command(name="givebraincells", description="Remove the braincell role from someone.")
async def givebraincells(interaction: discord.Interaction, user: discord.Member):
    """Removes the temporary role from the specified user."""
    executor = interaction.user
    guild = interaction.guild

    # Check if the executor has the required role to use this command
    required_role = guild.get_role(DAILY_ROLE_ID)
    if required_role not in executor.roles:
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return

    temp_role = guild.get_role(TEMP_ROLE_ID)
    if temp_role:
        if temp_role in user.roles:
            await user.remove_roles(temp_role)
            await interaction.response.send_message(f"Removed the braincell role from {user.mention}.")
            print(f"Removed temporary role from {user}")
        else:
            await interaction.response.send_message(f"{user.mention} doesn't have the braincell role.", ephemeral=True)
    else:
        await interaction.response.send_message("Temporary role not found.", ephemeral=True)



if __name__ == "__main__":
    # Start the keep-alive server BEFORE starting the bot
    keep_alive()

    # --- YOUR DISCORD BOT INITIALIZATION AND bot.run() CALL GOES HERE ---
    # Make sure your bot's token and startup logic is placed below this line.
    # ---------------------------------------------------------------------
    bot.run(TOKEN)
