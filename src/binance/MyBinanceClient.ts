import { MainClient, WebsocketClient, KlinesParams, Kline } from "binance";
import MyDiscordClient from "../discord/MyDiscordClient";
import CryptoManager from "../crypto/CryptoManager";
const dotenv = require("dotenv");

dotenv.config();

class MyClient {
  private static instance: MyClient;
  public client: MainClient;
  public wsClient: WebsocketClient;

  private constructor() {
    console.log("MyBinanceClient constructor");
    const API_KEY = process.env.API_KEY;
    const API_SECRET = process.env.API_SECRET;

    if (!API_KEY || !API_SECRET) {
      throw new Error("API_KEY or API_SECRET not found in .env file");
    }

    this.client = new MainClient({
      api_key: API_KEY,
      api_secret: API_SECRET,
    });

    this.wsClient = new WebsocketClient({
      api_key: API_KEY,
      api_secret: API_SECRET,
      beautify: true,
    });

    this.wsClient.on("formattedMessage", (data: any) => {
      if (data.eventType === "kline") {
        const symbol = data.symbol;
        const kline = data.kline;
        CryptoManager.getCrypto(symbol).receivedNewKline(kline);
      }
    });
  }

  public static getInstance(): MyClient {
    if (!MyClient.instance) {
      MyClient.instance = new MyClient();
    }

    return MyClient.instance;
  }

  public async start() {
    console.log("Binance client is starting...");

    const currTime = Math.floor(Date.now());
    await Promise.all(
      CryptoManager.currentCryptoList.map(async (symbol: string) => {
        const params: KlinesParams = {
          symbol,
          interval: "1h",
          startTime: currTime - 1000 * 3600 * 24, // 24 hours ago
        };

        return this.client
          .getKlines(params)
          .then((klines: Kline[]) => {
            CryptoManager.getCrypto(symbol).loadHistoricalKlines(klines);
          })
          .catch((err: any) => {
            console.error("error getKlines: ", err);
          });
      })
    );

    CryptoManager.currentCryptoList.forEach((symbol: string) => {
      this.wsClient.subscribeSpotKline(symbol, "1m");
    });

    console.log("Binance client finished setting up.");
  }
}

export default MyClient.getInstance();
