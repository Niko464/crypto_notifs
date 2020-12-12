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




global crypto_list
global bsm
global client
global is_ready_to_receive_new_msg
crypto_list = {}
client = Client(private_config.API_KEY, private_config.API_SECRET)
is_ready_to_receive_new_msg = True

def load_config(file):
	try:
		with open(file) as json_file:
			json_data = json.load(json_file)
			for crypto in json_data["crypto_list"]:
				crypto_list[crypto] = {"symbol": crypto}
	except Exception as e:
		print("Error while loading config: " + file + " exiting...")
		print("Exception: " + str(e))
		sys.exit(-1)

def download_history():
	for symbol in crypto_list:
		crypto = crypto_list[symbol]
		print("Downloading history of " + str(symbol) + "...")
		candlesticks = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1MINUTE, "1 Day Ago")
		crypto["prices"] = {}
		crypto["min_24h"] = (0, float(sys.maxsize))
		crypto["max_24h"] = (0, float(-sys.maxsize))
		crypto["min_4h"] = (0, float(sys.maxsize))
		crypto["max_4h"] = (0, float(-sys.maxsize))
		crypto["min_1h"] = (0, float(sys.maxsize))
		crypto["max_1h"] = (0, float(-sys.maxsize))
		crypto["last_notif_price"] = 0
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
	bsm = BinanceSocketManager(client)

	for symbol in crypto_list:
		crypto = crypto_list[symbol]
		crypto["stream_key"] = bsm.start_kline_socket(symbol, received_price_msg, interval=Client.KLINE_INTERVAL_1MINUTE)

	bsm.start()

def received_price_msg(msg):
	try:
		if msg['e'] != 'error':
			global is_ready_to_receive_new_msg
			if is_ready_to_receive_new_msg == True:
				is_ready_to_receive_new_msg = False
				received_price(msg['s'], msg['k']['t'], float(msg['k']['c']))
				is_ready_to_receive_new_msg = True
		else:
			comm.report_error(msg="Error 'B' with the price getter info...",
				mail=False, console=True, log=True, telegram=True, quit=False)
	except Exception as e:
		comm.report_error(msg="Error 'A' with the price getter info Error: " + str(e) + "\nMsg received: " + str(msg),
			mail=False, console=True, log=True, telegram=True, quit=False)

def received_price(symbol, timestamp, price):
	crypto = crypto_list[symbol]
	if timestamp in crypto["prices"]:
		crypto["prices"][timestamp] = price
	else:
		comm.communicate(msg=str(symbol) + " | Updating " + str(timestamp) + ", price: " + str(price),
			mail=False, console=True, telegram=False, log=True)
		crypto["prices"][int(timestamp)] = price
		if (len(crypto["prices"]) > 1440): # There are 1440 minutes in a day
			crypto["prices"].pop(timestamp - (3600000 * 24)) # 3600000 is 1 hour in milliseconds
	# Checking if current records are outdated
	if (crypto["max_1h"][0] + 3600000 < timestamp):
		crypto["max_1h"] = find_new_record(timestamp, '1h', crypto["prices"], 'High')
	if (crypto["min_1h"][0] + 3600000 < timestamp):
		crypto["min_1h"] = find_new_record(timestamp, '1h', crypto["prices"], 'Low')
	if (crypto["max_4h"][0] + 3600000 < timestamp):
		crypto["max_4h"] = find_new_record(timestamp, '4h', crypto["prices"], 'High')
	if (crypto["min_4h"][0] + 3600000 < timestamp):
		crypto["min_4h"] = find_new_record(timestamp, '4h', crypto["prices"], 'Low')
	if (crypto["max_24h"][0] + (3600000 * 24) < timestamp):
		crypto["max_24h"] = find_new_record(timestamp, '24h', crypto["prices"], 'High')
	if (crypto["min_24h"][0] + (3600000 * 24) < timestamp):
		crypto["min_24h"] = find_new_record(timestamp, '24h', crypto["prices"], 'Low')
	
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
		comm.communicate(msg=f"{symbol} --> {timeframe} New {record_type}: {price}", mail=False, console=True, telegram=True, log=True)
		crypto["last_notif_price"] = price

def find_new_record(timestamp, timeframe, prices, record_type):
	try:
		record = (0, sys.maxsize) if record_type == 'Low' else (0, -sys.maxsize - 1)
		for i in range(0, (60 if timeframe == '1h' else (240 if timeframe == '4h' else 1440))):
			test_timestamp = timestamp - (i * 60000)
			if (record_type == 'Low'):
				if prices[test_timestamp] < record[1]:
					record = (test_timestamp, prices[test_timestamp])
			else:
				if prices[test_timestamp] > record[1]:
					record = (test_timestamp, prices[test_timestamp])
		
		#comm.communicate(msg="TEST timestamp: " + str(timestamp) + " record_type: " + record_type + " time_frame: " + timeframe + " New record found: " + str(record), mail=False, console=False, telegram=True, log=True)
		return record
	except Exception as e:
		comm.report_error(msg="Caught exception: " + str(e), mail=False, console=True, log=True, telegram=True, quit=False)

@tasks.loop(seconds=1)
async def my_background_task():
	channel = config.disc_client.get_channel(private_config.DISCORD_NOTIF_CHANNEL)
	while len(config.discord_msgs_buffer) > 0:
		await channel.send(config.discord_msgs_buffer[0])
		config.discord_msgs_buffer.pop(0)



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
	load_config(config_file)
	download_history()
	start_data_streams()
	comm.communicate(msg="Finished loading!", mail=False, console=True, telegram=True if (config.RELEASE_MODE) else False, log=True)
	config.disc_client.run(private_config.DISCORD_TOKEN)

@config.disc_client.event
async def on_ready():
	my_background_task.start()
	print(f"Discord bot connected!")

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
