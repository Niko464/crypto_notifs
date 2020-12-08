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




global crypto_list
global bsm
global client
crypto_list = {}
client = Client(private_config.API_KEY, private_config.API_SECRET)

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
		crypto["min_1h"] = (0, float(sys.maxsize))
		crypto["max_1h"] = (0, float(-sys.maxsize))
		for candlestick in candlesticks:
			#TOHLC - Time, Open, High, Low, Close
			if (float(candlestick[2]) > crypto["max_24h"][1]):
				crypto["max_24h"] = (int(candlestick[0]), float(candlestick[2]))
			elif (float(candlestick[3]) < crypto["min_24h"][1]):
				crypto["min_24h"] = (int(candlestick[0]), float(candlestick[3]))
		for i in range(60, 0, -1):
			candlestick = candlesticks[-i]
			if (float(candlestick[2]) > crypto["max_1h"][1]):
				crypto["max_1h"] = (int(candlestick[0]), float(candlestick[2]))
			elif (float(candlestick[3]) < crypto["min_1h"][1]):
				crypto["min_1h"] = (int(candlestick[0]), float(candlestick[3]))
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
			received_price(msg['s'], msg['k']['t'], float(msg['k']['c']))
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
		if (len(crypto["prices"]) > 60):
			crypto["prices"].pop(timestamp - 3600000) # 3600000 is 1 hour in milliseconds
	if (price > crypto["max_1h"][1]):
		crypto["max_1h"] = (int(timestamp), price)
		comm.communicate(msg="1h New High: " + str(price), mail=False, console=True, telegram=True, log=True)
		if (price > crypto["max_24h"][1]):
			crypto["max_24h"] = (int(timestamp), price)
			comm.communicate(msg="24h New High: " + str(price), mail=False, console=True, telegram=True, log=True)
	elif (price < crypto["min_1h"][1]):
		crypto["min_1h"] = (int(timestamp), price)
		comm.communicate(msg="1h New Low: " + str(price), mail=False, console=True, telegram=True, log=True)
		if (price < crypto["min_24h"][1]):
			crypto["min_24h"] = (int(timestamp), price)
			comm.communicate(msg="24h New Low: " + str(price), mail=False, console=True, telegram=True, log=True)

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