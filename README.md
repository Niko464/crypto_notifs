# crypto_notifs

## <ins> Disclaimer

I will not support this repository. Use it only if you want.

## <ins> Introduction

This project is about getting notification of price movements in selected crypto markets, the notifications are sent through
a discord server bot.
It works by using binance's api to get the real time prices and parses those prices before sending notifications.

## <ins>Usage

To launch the project I use this command:

nohup python3 main.py ./configs/default.json &

## <ins> Notes

For the project to run, you need a .env file with:

API_KEY

API_SECRET

DISCORD_TOKEN

DISCORD_SECRET

DISCORD_GUILD_NAME
