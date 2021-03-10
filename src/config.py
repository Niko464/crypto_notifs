import discord
from discord.ext import commands

RELEASE_MODE = False
LOG_DIRECTORY = "logs/"
BOT_NAME = "Notifs"
CONTROL_CHANNEL_NAME = "crypto_notifs"
MIN_MOVEMENT_PERCENTAGE_FOR_NOTIF = 1.0


global disc_client
disc_client = commands.Bot(command_prefix='!') #discord.Client()
global discord_msgs_buffer
discord_msgs_buffer = []