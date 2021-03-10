import sys
import os
import json
import logging
from datetime import datetime
import datetime as dt
import src.private_config as private_config
import src.communication_module as comm
import src.config as config
from binance.client import Client
from binance.websockets import BinanceSocketManager
from binance.exceptions import *
import discord
from discord.ext import tasks
import asyncio
import traceback
import time



global main_info
global crypto_list
global options
global CONFIG_FILE_PATH
CONFIG_FILE_PATH = ""
main_info = {}
crypto_list = {}
options = {}

def curr_time():
	return time.time() * 1000

def load_config(file):
	try:
		with open(file) as json_file:
			json_data = json.load(json_file)
			for crypto_elem in json_data["crypto_list"]:
				crypto_list[crypto_elem["symbol"]] = crypto_elem
			print(str(crypto_list[crypto_elem["symbol"]]))
			for key, value in json_data["options"].items():
				options[key] = value
	except Exception as e:
		print("Error while loading config: " + file + " exiting...")
		print("Exception: " + str(e))
		sys.exit(-1)

def save_config(file):
	try:
		data = {}
		data["crypto_list"] = []
		data["options"] = {}
		for symbol in crypto_list:
			crypto = crypto_list[symbol]
			data["crypto_list"].append({"symbol": crypto["symbol"], "options": crypto["options"]})
		for key, value in options.items():
			data["options"][key] = value
		with open(file, 'w') as file:
			json.dump(data, file)
	except Exception as e:
		comm.report_error(msg="Error while saving config: " + file + " exiting... " + str(e),
			mail=False, console=True, log=True, telegram=True, quit=True, discord_channel=main_info["control_channel"])

def download_history_one_crypto(crypto, symbol):
	print("Downloading history of " + str(symbol) + "...")
	candlesticks = main_info["binance_client"].get_historical_klines(symbol, Client.KLINE_INTERVAL_1MINUTE, "1 Day Ago")
	crypto["prices"] = {}
	crypto["min_24h"] = (0, float(sys.maxsize))
	crypto["max_24h"] = (0, float(-sys.maxsize))
	crypto["min_4h"] = (0, float(sys.maxsize))
	crypto["max_4h"] = (0, float(-sys.maxsize))
	crypto["min_1h"] = (0, float(sys.maxsize))
	crypto["max_1h"] = (0, float(-sys.maxsize))
	crypto["personal_notification_prices"] = []
	crypto["last_received_price"] = float(candlesticks[-1][4])
	crypto["last_notif_price"] = 0
	crypto["last_10secs_prices"] = []
	crypto["last_notification_record_time"] = 0
	for i in range(len(candlesticks), 0, -1):
		candlestick = candlesticks[-i]
		#TOHLC - Time, Open, High, Low, Close
		if (i <= 60):
			if (float(candlestick[2]) > crypto["max_1h"][1]):
				crypto["max_1h"] = (int(candlestick[0]), float(candlestick[2]))
			elif (float(candlestick[3]) < crypto["min_1h"][1]):
				crypto["min_1h"] = (int(candlestick[0]), float(candlestick[3]))
		if (i <= 240):
			if (float(candlestick[2]) > crypto["max_4h"][1]):
				crypto["max_4h"] = (int(candlestick[0]), float(candlestick[2]))
			elif (float(candlestick[3]) < crypto["min_4h"][1]):
				crypto["min_4h"] = (int(candlestick[0]), float(candlestick[3]))
		if (i <= 1440):
			if (float(candlestick[2]) > crypto["max_24h"][1]):
				crypto["max_24h"] = (int(candlestick[0]), float(candlestick[2]))
			elif (float(candlestick[3]) < crypto["min_24h"][1]):
				crypto["min_24h"] = (int(candlestick[0]), float(candlestick[3]))
		crypto["prices"][int(candlestick[0])] = float(candlestick[4])

def start_data_streams():
	main_info["bsm"] = BinanceSocketManager(main_info["binance_client"])

	for symbol in crypto_list:
		crypto = crypto_list[symbol]
		crypto["stream_key"] = main_info["bsm"].start_kline_socket(symbol, received_price_msg, interval=Client.KLINE_INTERVAL_1MINUTE)

	main_info["bsm"].start()

def received_price_msg(msg):
	try:
		if msg['e'] != 'error':
			if main_info["is_ready_to_receive_new_msg"] == True:
				main_info["is_ready_to_receive_new_msg"] = False
				received_price(msg['s'], msg['k']['t'], float(msg['k']['c']))
				main_info["is_ready_to_receive_new_msg"] = True
		else:
			comm.report_error(msg="Error 'B' with the price getter info...",
				mail=False, console=True, log=True, telegram=True, quit=False, discord_channel=main_info["control_channel"])
	except Exception as e:
		comm.report_error(msg="Error 'A' with the price getter info Error: " + str(e) + "\nTraceback: " + str(traceback.format_exc()),
			mail=False, console=True, log=True, telegram=True, quit=False, discord_channel=main_info["control_channel"])

def received_price(symbol, timestamp, price):
	crypto = crypto_list[symbol]
	crypto["last_received_price"] = price
	# Checking personal notifications
	for notification_elem in list(crypto["personal_notification_prices"]):
		if ((notification_elem[0] > notification_elem[1]) and (price < notification_elem[1])) or\
			((notification_elem[0] < notification_elem[1]) and (price > notification_elem[1])):
			comm.communicate(msg=f"!notify cmd: {symbol} crossed {notification_elem[1]} current price: {price}", mail=False, console=True, telegram=True, log=True, discord_channel=crypto["channel"])
			crypto["personal_notification_prices"].remove(notification_elem)
	# Updating price history
	if timestamp in crypto["prices"]:
		crypto["prices"][timestamp] = price
	else:
		crypto["prices"][int(timestamp)] = price
		counter = 0
		while (len(crypto["prices"]) > 1440): # There are 1440 minutes in a day
			try:
				crypto["prices"].pop(timestamp - (3600000 * 24) + (60000 * counter)) # 3600000 is 1 hour in milliseconds
				counter += 1
			except KeyError as e:
				continue
	# Checking if current records are outdated
	if (crypto["max_1h"][0] + 3600000 < timestamp):
		crypto["max_1h"] = find_new_record(timestamp, '1h', crypto["prices"], 'High')
	if (crypto["min_1h"][0] + 3600000 < timestamp):
		crypto["min_1h"] = find_new_record(timestamp, '1h', crypto["prices"], 'Low')
	if (crypto["max_4h"][0] + (3600000 * 4) < timestamp):
		crypto["max_4h"] = find_new_record(timestamp, '4h', crypto["prices"], 'High')
	if (crypto["min_4h"][0] + (3600000 * 4) < timestamp):
		crypto["min_4h"] = find_new_record(timestamp, '4h', crypto["prices"], 'Low')
	if (crypto["max_24h"][0] + (3600000 * 24) < timestamp):
		crypto["max_24h"] = find_new_record(timestamp, '24h', crypto["prices"], 'High')
	if (crypto["min_24h"][0] + (3600000 * 24) < timestamp):
		crypto["min_24h"] = find_new_record(timestamp, '24h', crypto["prices"], 'Low')
	# Price movement detector
	crypto["last_10secs_prices"].append(price)
	if (len(crypto["last_10secs_prices"]) > 10):
		crypto["last_10secs_prices"].pop(0)
		if curr_time() - 300000 < crypto["last_notification_record_time"]: # if it has been less than 5 minutes since the last record notif
			record = {"percentage": 0.0, "time_ago": 0, "direction": "None"}
			for i in range(0, 9):
				percentage = (price - crypto["last_10secs_prices"][i]) / crypto["last_10secs_prices"][i] * 100
				is_negative = False
				if percentage < 0:
					percentage *= -1
					is_negative = True
				if percentage > record["percentage"]:
					record["percentage"] = percentage
					record["time_ago"] = i
					record["direction"] = "Up" if is_negative == False else "Down"
			if record["percentage"] > config.MIN_MOVEMENT_PERCENTAGE_FOR_NOTIF:
				msg = symbol + " --> High volatility going " + record["direction"] + "! " + str(round(record["percentage"], 2)) + "% in the last " + str(record["time_ago"] + 1) + " seconds (" + str(crypto["last_10secs_prices"][record["time_ago"]]) + " --> " + str(price) + ")."
				comm.communicate(msg=msg, mail=False, console=True, telegram=True, log=True, discord_channel=crypto["channel"])
	# Checking if current price is a record
	if (price > crypto["max_1h"][1]):
		crypto["max_1h"] = (int(timestamp), price)
		if (price > crypto["max_4h"][1]):
			crypto["max_4h"] = (int(timestamp), price)
			if (price > crypto["max_24h"][1]):
				crypto["max_24h"] = (int(timestamp), price)
				new_record(symbol, '24h', 'High', price, crypto)
			else:
				new_record(symbol, '4h', 'High', price, crypto)
		else:
			new_record(symbol, '1h', 'High', price, crypto)
	elif (price < crypto["min_1h"][1]):
		crypto["min_1h"] = (int(timestamp), price)
		if (price < crypto["min_4h"][1]):
			crypto["min_4h"] = (int(timestamp), price)
			if (price < crypto["min_24h"][1]):
				crypto["min_24h"] = (int(timestamp), price)
				new_record(symbol, '24h', 'Low', price, crypto)
			else:
				new_record(symbol, '4h', 'Low', price, crypto)
		else:
			new_record(symbol, '1h', 'Low', price, crypto)

def new_record(symbol, timeframe, record_type, price, crypto):
	diff = crypto["last_notif_price"] - price
	if (diff < 0):
		diff *= -1
	if (diff / price >= 0.002): #0.002 is for 0.2% difference this could be a variable but flemme
		comm.communicate(msg=f"{symbol} --> {timeframe} New {record_type}: {price}", mail=False, console=True, telegram=True if (options[timeframe + "_notifs"] == 1) and (crypto["options"][timeframe + "_notifs"] == 1) else False, log=True, discord_channel=crypto["channel"])
		if (options[timeframe + "_notifs"] == 1) and (crypto["options"][timeframe + "_notifs"] == 1):
			crypto["last_notification_record_time"] = curr_time()
		crypto["last_notif_price"] = price

def find_new_record(timestamp, timeframe, prices, record_type):
	record = (0, sys.maxsize) if record_type == 'Low' else (0, -sys.maxsize - 1)
	for i in range(0, (60 if timeframe == '1h' else (240 if timeframe == '4h' else 1440))):
		try:
			test_timestamp = timestamp - (i * 60000)
			if (record_type == 'Low'):
				if prices[test_timestamp] < record[1]:
					record = (test_timestamp, prices[test_timestamp])
			else:
				if prices[test_timestamp] > record[1]:
					record = (test_timestamp, prices[test_timestamp])
		except KeyError as e:
			comm.report_error(msg="There was a key error: " + str(e), mail=False, console=True, log=True, telegram=False, quit=False)
			continue
	comm.communicate(msg="find new_record: " + str(timestamp) + " record_type: " + record_type + " time_frame: " + timeframe + " New record found: " + str(record), mail=False, console=False, telegram=False, log=True)
	return record

@tasks.loop(seconds=1)
async def my_task():
	while len(config.discord_msgs_buffer) > 0:
		await config.discord_msgs_buffer[0]["channel"].send(config.discord_msgs_buffer[0]["msg"])
		config.discord_msgs_buffer.pop(0)

@config.disc_client.command(name="add_crypto")
async def add_crypto_command(ctx, *args):
	usage_str = "Usage: !add_crypto <name>"
	if len(args) == 1:
		try:
			symbol = args[0]
			avg_price = main_info["binance_client"].get_symbol_ticker(symbol=symbol)["price"]
			await ctx.channel.send("Loading " + symbol + "...")
			crypto_list[symbol] = {"symbol": symbol}
			crypto = crypto_list[symbol]
			crypto["options"] = {}
			crypto["options"]["1h_notifs"] = 0
			crypto["options"]["4h_notifs"] = 1
			crypto["options"]["24h_notifs"] = 1
			await get_discord_channel(ctx.guild, symbol)
			download_history_one_crypto(crypto, symbol)
			crypto["stream_key"] = main_info["bsm"].start_kline_socket(symbol, received_price_msg, interval=Client.KLINE_INTERVAL_1MINUTE)
			save_config(CONFIG_FILE_PATH)
			await ctx.channel.send("Added " + symbol + " to the crypto_list.")
		except Exception as e:
			await ctx.channel.send("An error occurred, does the crypto exist on Binance ?")
			print("Caught an exception: " + str(e))
	else:
		await ctx.channel.send(usage_str)

@config.disc_client.command(name="notify")
async def notify_command(ctx, *args):
	usage_str = "Usage: !notify <add/remove/list> <coin ex: ETHUSDT> <price ex: 580>"
	if len(args) == 3:
		try:
			crypto = crypto_list[args[1]]
			notify_price = float(args[2])
			if (args[0].lower() == "add"):
				crypto["personal_notification_prices"].append((crypto["last_received_price"], notify_price))
				await ctx.channel.send("Added " + args[2] + " to " + args[1] + "'s notification list.")
			elif(args[0].lower() == "remove"):
				counter = 0
				for notification_elem in list(crypto["personal_notification_prices"]):
					if (notify_price == notification_elem[1]):
						crypto["personal_notification_prices"].remove(notification_elem)
						counter += 1
				await ctx.channel.send("Removed all " + args[2] + " from " + args[1] + "'s notification list (" + str(counter) + " elements removed).")
		except:
			await ctx.channel.send(usage_str)
	elif (len(args) == 2):
		try:
			crypto = crypto_list[args[1]]
			if (args[0].lower() == 'list'):
				if (len(crypto["personal_notification_prices"]) > 0):
					await ctx.channel.send("Here is the list:")
					for notification_elem in crypto["personal_notification_prices"]:
						await ctx.channel.send("- " + str(notification_elem[1]))
				else:
					await ctx.channel.send("No elements found in " + args[1] + "' notification list.")
			else:
				await ctx.channel.send(usage_str) 
		except:
			await ctx.channel.send(usage_str)
	else:
		await ctx.channel.send(usage_str)

@config.disc_client.command(name="options")
async def options_command(ctx, *args):
	usage_str = "Usage: !options <'main' or symbol ex: main/ETHUSDT> <set/list> <option name> <value (1 or 0 for bools)>"
	if len(args) == 4:
		category = args[0]
		if category.lower() == "main":
			if args[1].lower() == "set":
				try:
					option_name = args[2]
					option_value = float(args[3])
					if option_name in options:
						options[option_name] = option_value
						save_config(CONFIG_FILE_PATH)
						await ctx.channel.send("Changed option " + option_name + " to " + args[3] + ".")
					else:
						await ctx.channel.send("Option " + option_name + " not found.")
				except:
					await ctx.channel.send(usage_str)
			else:
				await ctx.channel.send(usage_str)
		elif category.upper() in crypto_list:
			if args[1].lower() == "set":
				try:
					option_name = args[2]
					option_value = float(args[3])
					crypto = crypto_list[category]
					if option_name in crypto["options"]:
						crypto["options"][option_name] = option_value
						save_config(CONFIG_FILE_PATH)
						await ctx.channel.send("Changed option " + option_name + " to " + args[3] + " for " + category + ".")
					else:
						await ctx.channel.send("Option " + option_name + " not found.")
				except Exception as e:
					await ctx.channel.send(usage_str)
					print("Exception: " + str(e))
			else:
				await ctx.channel.send(usage_str)
		else:
			await ctx.channel.send(usage_str)
	elif (len(args) == 2):
		category = args[0]
		if category.lower() == "main":
			if args[1].lower() == "list":
				await ctx.channel.send("Here are the available options\n- option_name | option_value")
				for key, value in options.items():
					await ctx.channel.send("- " + str(key) + " | " + str(value))
			else:
				await ctx.channel.send(usage_str)
		elif category.upper() in crypto_list:
			if args[1].lower() == "list":
				await ctx.channel.send("Available options for " + category + ":")
				for key, value in crypto_list[category]["options"].items():
					await ctx.channel.send("- " + str(key) + " | " + str(value))
			else:
				await ctx.channel.send(usage_str)
		else:
			await ctx.channel.send(usage_str)
	else:
		await ctx.channel.send(usage_str)

async def check_discord_channels(guild):
	print("Checking channels...")
	main_info["control_channel"] = discord.utils.get(guild.channels, name=config.CONTROL_CHANNEL_NAME)
	for symbol in crypto_list:
		await get_discord_channel(guild, symbol)

async def get_discord_channel(guild, symbol):
	channel = discord.utils.get(guild.channels, name=symbol.lower())
	while (channel == None):
		await guild.create_text_channel(symbol.lower())
		channel = discord.utils.get(guild.channels, name=symbol.lower())
	crypto_list[symbol]["channel"] = channel
			



def main(config_file = "configs/default.json"):
	if not (os.path.exists(config.LOG_DIRECTORY)):
		os.mkdir(config.LOG_DIRECTORY)
	logging.basicConfig(filename=config.LOG_DIRECTORY +
								datetime.now().strftime(\
								"%d-%m-%Y__%H-%M__") +
								"log",
                        filemode='a',
                        format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S |',
                        level=logging.DEBUG)
	logging.getLogger("requests").setLevel(logging.WARNING)
	logging.getLogger("urllib3").setLevel(logging.WARNING)
	logging.getLogger("discord").setLevel(logging.WARNING)
	global CONFIG_FILE_PATH
	CONFIG_FILE_PATH = config_file
	main_info["is_ready_to_receive_new_msg"] = True
	main_info["binance_client"] = Client(private_config.API_KEY, private_config.API_SECRET)
	main_info["bsm"] = None
	load_config(config_file)
	for symbol in crypto_list:
		download_history_one_crypto(crypto=crypto_list[symbol], symbol=symbol)
	config.disc_client.run(private_config.DISCORD_TOKEN)
	

@config.disc_client.event
async def on_ready():
	my_task.start()
	await check_discord_channels(config.disc_client.get_guild(private_config.DISCORD_GUILD_NAME))
	start_data_streams()
	comm.communicate(msg="Finished loading!", mail=False, console=True, telegram=True if (config.RELEASE_MODE) else False, log=True, discord_channel=main_info["control_channel"])

if __name__ == "__main__":
	argv = sys.argv
	if (len(argv) > 1):
		if (os.path.exists(argv[1])):
			print("Config file: " + str(argv[1]))
			main(argv[1])
		else:
			print("This file doesn't exist: ")
			print("Starting with default config...")
			main()
	else:
		print("No config file given, loading defualt one...")
		main()
