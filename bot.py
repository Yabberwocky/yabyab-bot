import discord
from discord.ext import commands, tasks
import asyncio
import datetime
import os
import logging
from flask import Flask
import threading
import traceback
from discord import app_commands
import random

# Load token from environment - IMPORTANT: Ensure this is set correctly in Render
TOKEN = os.getenv("DISCORD_TOKEN")

# Discord settings - Double check these IDs in your Discord server!
IMAGE_CHANNEL_ID = 1359782718426316840
DAILY_ROLE_ID = 1368237860326473859
TEMP_ROLE_ID = 1368238029571100834
GUILD_ID = 1200476681803137024
LOG_CHANNEL_ID = 1362988767367135453  # Added log channel ID

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to store the time when a user received the daily role
user_daily_role_times = {}

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


# --- Flask App (Keep Alive) ---
app = Flask('')

@app.route('/')
def home():
    return "Discord bot is alive!"

def run_flask():
    try:
        port = int(os.environ.get('PORT', 8080))
        logger.info(f"Starting Flask keep-alive server on host 0.0.0.0:{port}")
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        logger.error(f"Flask keep-alive server failed: {e}")

def keep_alive():
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
brainrot_messages = []
brainrot_task = None


async def stop_brainrot():
    """Stops the brainrot mode and resets the global variable."""
    global brainrot_active
    global brainrot_task
    global brainrot_messages
    if brainrot_task:
        try:
            brainrot_task.cancel()
        except Exception as e:
            logger.error(f"Error cancelling brainrot task: {e}")
    brainrot_active = False
    brainrot_task = None
    for msg in brainrot_messages:
        try:
            await msg.delete()
        except discord.NotFound:
            logger.warning(f"Message {msg.id} not found, was probably deleted already.")
        except Exception as e:
            logger.error(f"Error deleting message {msg.id}: {e}")
    brainrot_messages.clear()
    logger.info("Brainrot mode stopped.")


def randomize_caps(word):
    """Randomly capitalize letters in a word."""
    result = ""
    for char in word:
        if random.choice([True, False]):
            result += char.upper()
        else:
            result += char.lower()
    return result


@bot.tree.command(name="brainrot", description="Activates brainrot mode for 3 minutes.")
async def brainrot_command(interaction: discord.Interaction):
    """Activates brainrot mode."""
    global brainrot_active
    global brainrot_task
    global brainrot_messages
    try:
        # Check for the daily role
        if not await has_daily_role(interaction.user):
            await interaction.response.send_message(
                "You do not have permission to use this command.",
                ephemeral=True
            )
            return

        if brainrot_active:
            await interaction.response.send_message(
                "Brainrot mode is already active!",
                ephemeral=True
            )
            return

        brainrot_active = True
        await interaction.response.defer()

        async def send_brainrot_messages():
            while brainrot_active:
                try:
                    random_word = random.choice(brainrot_words)
                    random_word = randomize_caps(random_word)  # Capitalize randomly
                    msg = await interaction.channel.send(random_word)
                    brainrot_messages.append(msg)
                    await asyncio.sleep(10)
                except Exception as e:
                    logger.error(f"Error in send_brainrot_messages: {e}")
                    break

        brainrot_task = asyncio.create_task(send_brainrot_messages())

        # Use asyncio.sleep *within* the command function.
        await asyncio.sleep(180)  # 3 minutes
        await stop_brainrot()
        await interaction.followup.send("Brainrot mode has ended.")

    except Exception as e:
        logger.error(f"Error in brainrot_command: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "An error occurred while processing this command.",
                ephemeral=True
            )
        else:
            await interaction.followup.send("An error occurred.")



async def has_daily_role(user: discord.Member) -> bool:
    """Check if a user has the daily role."""
    daily_role = discord.utils.get(user.guild.roles, id=DAILY_ROLE_ID)
    return daily_role in user.roles


@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        logger.error(f"Guild with ID {GUILD_ID} not found.")
        return

    try:
        bot.tree.clear_commands(guild=guild)
        await bot.tree.sync(guild=guild)
        logger.info(f'Cleared and synced commands for guild {guild.name} ({guild.id})')

        try:
            await bot.tree.sync()
            logger.info("Successfully synced application commands globally.")
        except Exception as e:
            logger.error(f"Failed to sync application commands globally: {e}")
    except Exception as e:
        logger.error(
            f'Failed to sync commands for guild {guild.name} ({guild.id}): {e}\n{traceback.format_exc()}')
    daily_role_removal_task.start()



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

    # Check if brainrot mode is active
    if brainrot_active:
        try:
            random_word = random.choice(brainrot_words)
            random_word = randomize_caps(random_word)  # Capitalize randomly
            msg = await message.channel.send(random_word)
            brainrot_messages.append(msg)
        except Exception as e:
            logger.error(f"Error sending brainrot message: {e}")

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
        response = await message.channel.send(
            f"{message.author.mention} shut up dumb fuck")
        await asyncio.sleep(5)
        await response.delete()

    try:
        await bot.process_commands(message)
    except Exception as e:
        logger.error(
            f"Error processing command in on_message: {e}\n{traceback.format_exc()}")


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
                        logger.info(
                            f"Removed daily role from {member} (after 12 hours)")
                    except Exception as e:
                        logger.error(f"Error removing role from {member}: {e}")



@bot.tree.command(name="takebraincells", description="Give a role to someone for 5 minutes.")
async def takebraincells(interaction: discord.Interaction, user: discord.Member):
    executor = interaction.user
    guild = interaction.guild

    try:
        # Use helper function for role check
        if not await has_daily_role(executor):
            await interaction.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True
            )
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
            await interaction.response.send_message(
                "Temporary role not found.",
                ephemeral=True
            )
    except Exception as e:
        logger.error(
            f"Error in takebraincells: {e}\n{traceback.format_exc()}")
        await interaction.response.send_message(
            "An error occurred while processing this command.",
            ephemeral=True
        )



@bot.tree.command(name="givebraincells", description="Remove the braincell role from someone.")
async def givebraincells(
        interaction: discord.Interaction,
        user: discord.Member):
    """Removes the temporary role from the specified user."""
    executor = interaction.user
    guild = interaction.guild
    try:
        # Use the helper function
        if not await has_daily_role(executor):
            await interaction.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True
            )
            return

        temp_role = guild.get_role(TEMP_ROLE_ID)
        if temp_role:
            if temp_role in user.roles:
                await user.remove_roles(temp_role)
                await interaction.response.send_message(
                    f"Removed the braincell role from {user.mention}.")
                logger.info(f"Removed temporary role from {user}")
            else:
                await interaction.response.send_message(
                    f"{user.mention} doesn't have the braincell role.",
                    ephemeral=True
                )
        else:
            await interaction.response.send_message(
                "Temporary role not found.",
                ephemeral=True
            )
    except Exception as e:
        logger.error(
            f"Error in givebraincells: {e}\n{traceback.format_exc()}")



@bot.tree.command(name="ghostping", description="Anonymously ghost pings a user.")
@app_commands.checks.cooldown(1, 3600)  # 1 hour cooldown (3600 seconds)
async def ghostping_command(interaction: discord.Interaction, target: discord.Member, *, reason: str = ""):
    """
    Anonymously ghost pings a user. The command sends a message
    mentioning the user, then deletes it, so they get a notification
    but no message is visible.

    Parameters:
        interaction: The interaction context.
        target: The user to ghost ping.
        reason: (Optional) Reason for the ghost ping. This is logged.
    """
    try:
        # Check for the daily role
        if not await has_daily_role(interaction.user):
            await interaction.response.send_message(
                "You do not have permission to use this command.",
                ephemeral=True
            )
            return

        # 1. Send the mention message
        message = await interaction.channel.send(target.mention)

        # 2. Delete the message
        await message.delete()

        # 3. Logging the ghost ping
        log_message = f"Anonymous ghost ping of {target.name} ({target.id}) by {interaction.user.name} ({interaction.user.id})"
        if reason:
            log_message += f" with reason: {reason}"
        logger.info(log_message)

        # 4. Optional: Confirmation in a non-visible way.
        if interaction.guild:
            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(f"Ghost pinged {target.mention} anonymously.")

        await interaction.response.send_message("Ghost ping sent.", ephemeral=True)

    except discord.Forbidden:
        await interaction.response.send_message(
            "I do not have permissions to send messages and/or delete them.",
            ephemeral=True,
        )
        logger.warning(
            f"Bot lacks permissions to ghost ping in channel {interaction.channel.name} ({interaction.channel.id})"
        )
    except discord.NotFound:
        await interaction.response.send_message(
            "I could not delete the message. The user will still have been notified.",
            ephemeral=True,
        )
        logger.error("Failed to delete ghost ping message.")
    except Exception as e:
        await interaction.response.send_message(
            "An unexpected error occurred. Check the logs.", ephemeral=True
        )
        logger.error(f"Error in ghostping_command: {e}\n{traceback.format_exc()}")



@bot.event
async def on_message_delete(self, message: discord.Message):
    """
    This event listener is used to detect if a ghost ping was deleted by someone else.
    """
    if message.author == self.bot.user:  # If the bot deleted the message, it's normal.
        return
    
    # Check if the message content was a user mention
    if message.mentions:
        mentioned_users = message.mentions
        #basic check
        logger.warning(f"Possible ghost ping detected in {message.channel.name}! Message by {message.author} mentioning: {', '.join(m.name for m in mentioned_users)} was deleted by someone else.")
        
        # More robust check (optional, requires message history):
        try:
            # Fetch the audit log.  Requires View Audit Log permission.
            async for entry in message.guild.audit_logs(limit=5, action=discord.AuditLogAction.message_delete):
                if entry.target == message.author:
                    #  Deleted by someone else, within a short time frame.
                    if (entry.created_at - message.created_at).total_seconds() < 5:  # 5 seconds
                        logger.critical(f"Definite ghost ping detected in {message.channel.name}! Message by {message.author} mentioning: {', '.join(m.name for m in mentioned_users)} was deleted by {entry.user}!")
                        break #important
        except discord.Forbidden:
            logger.info("Missing permissions to check audit logs.")
        except Exception as e:
            logger.error(f"Error checking audit logs: {e}")



if __name__ == "__main__":
    # Start the keep-alive server BEFORE starting the bot
    keep_alive()

    # --- YOUR DISCORD BOT INITIALIZATION AND bot.run() CALL GOES HERE ---
    # Make sure your bot's token and startup logic is placed below this line.
    # ---------------------------------------------------------------------
    bot.run(TOKEN)
