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

    await this.loadHistoricalKlines();

    CryptoManager.currentCryptoList.forEach((symbol: string) => {
      this.wsClient.subscribeSpotKline(symbol, "1m");
    });

    console.log("Binance client finished setting up.");
  }

  private async loadHistoricalKlines() {
    const numMinutes = 60 * 24;
    const endTime = Math.floor(Date.now());
    const startTime = endTime - 1000 * 60 * numMinutes;
    const limit = 360; // limit of klines per request (should be a multiple of numMinutes)

    await Promise.all(
      CryptoManager.currentCryptoList.map(async (symbol: string) => {
        for (let i = 0; i < numMinutes / limit; i++) {
          const params: KlinesParams = {
            symbol,
            interval: "1m",
            startTime: startTime + i * limit * 60 * 1000,
            endTime: startTime + (i + 1) * limit * 60 * 1000,
            limit,
          };

          await this.client
            .getKlines(params)
            .then((klines: Kline[]) => {
              CryptoManager.getCrypto(symbol).loadHistoricalKlines(klines);
            })
            .catch((err: any) => {
              console.error("error getKlines: ", err);
            });
        }
      })
    );
  }
}

export default MyClient.getInstance();
