import discord
from discord.ext import commands, tasks
import asyncio
import datetime
import os
import logging
from flask import Flask
import threading

# Load token from environment - IMPORTANT: Ensure this is set correctly in Render
TOKEN = os.getenv("DISCORD_TOKEN")  # Ensure this is set in Render!

# Discord settings - Double check these IDs in your Discord server!
IMAGE_CHANNEL_ID = 1359782718426316840
DAILY_ROLE_ID = 1368237860326473859
TEMP_ROLE_ID = 1368238029571100834

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Enable the members intent

bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to store the time when a user received the daily role
user_daily_role_times = {}

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,  # Set the desired logging level (e.g., INFO, DEBUG, ERROR)
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),  # Output to console
        # logging.FileHandler("discord_bot.log"),  # Optionally, log to a file
    ],
)
logger = logging.getLogger(__name__)


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
        logger.info(f"Starting Flask keep-alive server on host 0.0.0.0:{port}")
        # Use debug=False for production on Render
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        logger.error(f"Flask keep-alive server failed: {e}")

def keep_alive():
    """Creates and starts the Flask server in a background thread."""
    # daemon=True ensures the thread exits when the main bot process stops
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Keep-alive thread initiated.")


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
brainrot_messages = []  # Store brainrot messages globally
brainrot_task = None  # Store the task globally


async def stop_brainrot():
    """Stops the brainrot mode and resets the global variable."""
    global brainrot_active
    global brainrot_task
    global brainrot_messages  # Access the global list
    brainrot_active = False
    brainrot_task = None
    for msg in brainrot_messages:  # Delete stored messages
        try:
            await msg.delete()
        except discord.NotFound:
            logger.warning(f"Message {msg.id} not found, was probably deleted already.")
        except Exception as e:
            logger.error(f"Error deleting message {msg.id}: {e}")
    brainrot_messages.clear()  # Clear the list
    logger.info("Brainrot mode stopped.")


@bot.tree.command(name="brainrot", description="Activates brainrot mode for 3 minutes.")
async def brainrot_command(interaction: discord.Interaction):
    """Activates brainrot mode."""
    global brainrot_active
    global brainrot_task
    global brainrot_messages  # Access the global message list
    try:
        # Check for the daily role here!  Use a helper function
        if not await has_daily_role(interaction.user):
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return

        if brainrot_active:
            await interaction.response.send_message("Brainrot mode is already active!", ephemeral=True)
            return

        brainrot_active = True
        # Acknowledge the command *immediately*
        await interaction.response.defer()  # Add this line!
        await interaction.followup.send("Brainrot mode activated! Prepare for the cringe...")  # send followup

        # Create a new task and store it in the global variable
        brainrot_task = asyncio.create_task(asyncio.sleep(180))  # 3 minutes = 180 seconds

        async def send_brainrot_messages():  # helper function
            while brainrot_active:
                random_word = random.choice(brainrot_words)
                msg = await interaction.channel.send(random_word)
                brainrot_messages.append(msg)  # Append message to the list
                await asyncio.sleep(10)

        # Run the message sending as a separate task
        asyncio.create_task(send_brainrot_messages())

        # Schedule the task to stop brainrot after 3 minutes
        await asyncio.sleep(180)
        await stop_brainrot()
        await interaction.followup.send("Brainrot mode has ended.")  # send followup
    except Exception as e:
        logger.error(f"Error in brainrot_command: {e}")
        await interaction.response.send_message(
            "An error occurred while processing this command.", ephemeral=True
        )



async def has_daily_role(user: discord.Member) -> bool:
    """Check if a user has the daily role."""
    daily_role = discord.utils.get(user.guild.roles, id=DAILY_ROLE_ID)
    return daily_role in user.roles



@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
    try:
        # Clear all global commands first
        bot.tree.clear_commands(guild=None)  # Pass None to clear global commands
        await bot.tree.sync()  # Sync globally after clearing
        logger.info(f'Cleared and synced all commands globally')
    except Exception as e:
        logger.error(f'Failed to sync commands: {e}')
    daily_role_removal_task.start()
    try:
        await bot.tree.sync()
        logger.info("Successfully synced application commands.")
    except Exception as e:
        logger.error(f"Failed to sync application commands: {e}")



@bot.event
async def on_message(message):
    global brainrot_active
    global brainrot_words
    global brainrot_messages

    logger.info(
        f"on_message event triggered. Message from {message.author.name} in {message.channel.name} (Channel ID: {message.channel.id})")

    if message.author.bot:
        logger.info("Message author is a bot, ignoring.")
        return

    # Logic for assigning role on any message in the specified channel
    if message.channel.id == IMAGE_CHANNEL_ID:
        logger.info("Message is in the correct channel.")
        guild = message.guild
        user = message.author
        role = guild.get_role(DAILY_ROLE_ID)
        if role and role not in user.roles:
            try:
                await user.add_roles(role)
                now = datetime.datetime.now(datetime.timezone.utc)
                user_daily_role_times[user.id] = now
                logger.info(f"Assigned role {role.name} to {user.name} at {now}")
            except Exception as e:
                logger.error(f"Error adding role: {e}")

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
                    try:
                        await member.remove_roles(role)
                        logger.info(f"Removed daily role from {member} (after 12 hours)")
                    except Exception as e:
                        logger.error(f"Error removing role from {member}: {e}")



@bot.tree.command(name="takebraincells", description="Give a role to someone for 5 minutes.")
async def takebraincells(interaction: discord.Interaction, user: discord.Member):
    executor = interaction.user
    guild = interaction.guild

    try:
        # Use helper function for role check
        if not await has_daily_role(executor):
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
            logger.info(f"Removed temporary role from {user}")
        else:
            await interaction.response.send_message("Temporary role not found.", ephemeral=True)
    except Exception as e:
        logger.error(f"Error in takebraincells: {e}")
        await interaction.response.send_message("An error occurred while processing this command.", ephemeral=True)



@bot.tree.command(name="givebraincells", description="Remove the braincell role from someone.")
async def givebraincells(interaction: discord.Interaction, user: discord.Member):
    """Removes the temporary role from the specified user."""
    executor = interaction.user
    guild = interaction.guild
    try:
        # Use the helper function
        if not await has_daily_role(executor):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return

        temp_role = guild.get_role(TEMP_ROLE_ID)
        if temp_role:
            if temp_role in user.roles:
                await user.remove_roles(temp_role)
                await interaction.response.send_message(f"Removed the braincell role from {user.mention}.")
                logger.info(f"Removed temporary role from {user}")
            else:
                await interaction.response.send_message(f"{user.mention} doesn't have the braincell role.", ephemeral=True)
        else:
            await interaction.response.send_message("Temporary role not found.", ephemeral=True)
    except Exception as e:
        logger.error(f"Error in givebraincells: {e}")
        await interaction.response.send_message("An error occurred while processing this command.", ephemeral=True)



if __name__ == "__main__":
    # Start the keep-alive server BEFORE starting the bot
    keep_alive()

    # --- YOUR DISCORD BOT INITIALIZATION AND bot.run() CALL GOES HERE ---
    # Make sure your bot's token and startup logic is placed below this line.
    # ---------------------------------------------------------------------
    bot.run(TOKEN)
