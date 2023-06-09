import MyDiscordClient from "../discord/MyDiscordClient";
import CryptoManager from "./CryptoManager";
import { CircularBuffer } from "./utils/CircularBuffer";
import { Kline } from "binance";

export type PriceEntry = {
  timestamp: number;
  price: number;
};

export default class Crypto {
  private symbol: string;

  //records for the last x hours
  private minRecords: Map<number, PriceEntry> = new Map<number, PriceEntry>();
  private maxRecords: Map<number, PriceEntry> = new Map<number, PriceEntry>();
  private prices: CircularBuffer = new CircularBuffer(60 * 24); // 24 hours
  //the time at which the last price was received
  private lastReceivedPriceTime: number = 0;

  public constructor(symbol: string) {
    this.symbol = symbol;
  }

  public loadHistoricalKlines(klines: Kline[]) {
    klines.forEach((kline) => {
      this.prices.push({
        timestamp: kline[0],
        price: parseFloat(kline[4].toString()),
      });
    });
    this.updateAllRecords();
  }

  public receivedNewKline(kline: any) {
    if (kline.startTime <= this.lastReceivedPriceTime) {
      return;
    }
    this.lastReceivedPriceTime = kline.startTime;
    const price = parseFloat(kline.close.toString());
    this.prices.push({
      timestamp: kline.startTime,
      price: price,
    });

    this.checkRecords(price);
  }

  private checkRecords(newPrice: number) {
    //check if the current records are outdated
    //sort the times in descending order (to only send notifs for the biggest time)

    //booleans set to true if we sent a notification for this TYPE (high or low)
    let sentNotifHigh: boolean = false;
    let sentNotifLow: boolean = false;

    CryptoManager.surveillanceTimes
      .sort((a, b) => b - a)
      .forEach((time) => {
        let highRecord: PriceEntry | undefined = this.maxRecords.get(time);
        let lowRecord: PriceEntry | undefined = this.minRecords.get(time);

        if (!highRecord || !lowRecord) {
          console.error("Crypto.checkRecords: record not found");
          return;
        }

        if (highRecord.timestamp < this.lastReceivedPriceTime - time * 60) {
          highRecord = this.updateRecord(time, true);
        }
        if (lowRecord.timestamp < this.lastReceivedPriceTime - time * 60) {
          lowRecord = this.updateRecord(time, false);
        }

        /*
      check if the new price is a new record and send a notification if it is
      only if we haven't already sent a notification
      */
        if (!sentNotifHigh && newPrice > highRecord.price) {
          MyDiscordClient.sendRecordmessage(this.symbol, time, newPrice, true);
          sentNotifHigh = true;
        }
        if (!sentNotifLow && newPrice < lowRecord.price) {
          MyDiscordClient.sendRecordmessage(this.symbol, time, newPrice, false);
          sentNotifLow = true;
        }
      });
  }

  private updateAllRecords() {
    CryptoManager.surveillanceTimes.forEach((time) => {
      this.updateRecord(time, true);
      this.updateRecord(time, false);
    });
  }

  private updateRecord(time: number, highest: boolean): PriceEntry {
    const record: PriceEntry = this.prices.findRecord(time * 60, highest);

    if (highest) {
      this.maxRecords.set(time, record);
    } else {
      this.minRecords.set(time, record);
    }
    return record;
  }
}
