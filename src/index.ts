import MyBinanceClient from "./binance/MyBinanceClient";
import CryptoManager from "./crypto/CryptoManager";
import MyDiscordClient from "./discord/MyDiscordClient";




async function main() {
  await CryptoManager.start();
  await MyDiscordClient.start()
  await MyBinanceClient.start();
}

main()