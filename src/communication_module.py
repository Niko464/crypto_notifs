import smtplib
import requests
import logging
import time
import json
import sys
import src.private_config as private_config
import src.config as config
from requests.exceptions import Timeout


def send_mail_to_mailing_list(msg):
	try:
		with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
			smtp.ehlo()
			smtp.starttls()
			smtp.ehlo()
			smtp.login(private_config.EMAIL_ADDRESS, private_config.EMAIL_PASS)
			subject = 'Crypto notif BOT'
			body = msg
			complete_msg = f'Subject: {subject}\n\n{body}'
			for RECEIVER in config.mailing_list:
				smtp.sendmail(private_config.EMAIL_ADDRESS, RECEIVER, complete_msg)
	except:
		report_error(msg="MAIL FAIL -> Do you have internet ?", log=True, console=True, telegram=False, mail=False, quit=False)


"""
def send_telegram_message(msg_to_send):
	try:
		params = {"chat_id": private_config.TELEGRAM_CHAT_ID, "text": config.BOT_NAME + " | " + msg_to_send}
		response = requests.post(private_config.TELEGRAM_BOT_URL + "sendMessage", data=params)
		return response
	except:
		report_error(msg="TELEGRAM MSG FAIL -> Do you have internet ?", log=True, console=True, telegram=False, mail=False, quit=False)
"""


def report_error(msg, mail, telegram, console, log, quit):
	if (mail == True and config.RELEASE_MODE == True):
		send_mail_to_mailing_list(msg)
	if (telegram == True):
		#send_telegram_message(msg)
		config.discord_msgs_buffer.append(msg)
	if (console == True):
		print(msg)
	if (log == True):
		logging.error(msg)
	if (quit == True):
		sys.exit()



def communicate(msg, mail, telegram, console, log, discord_channel = None):
	if (mail == True and config.RELEASE_MODE == True):
		send_mail_to_mailing_list(msg)
	if (telegram == True):
		if (discord_channel != None):
			config.discord_msgs_buffer.append({"channel": discord_channel, "msg": msg})
	if (console == True):
		print(msg)
	if (log == True):
		logging.info(msg)



def debug(msg):
	print(msg)
	logging.debug(msg)