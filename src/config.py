import discord

RELEASE_MODE = True
LOG_DIRECTORY = "logs/"
BOT_NAME = "Notifs"


global disc_client
disc_client = discord.Client()
global discord_msgs_buffer
discord_msgs_buffer = []