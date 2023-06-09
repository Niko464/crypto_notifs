import { PriceEntry } from "../Crypto";

export class CircularBuffer {
  private arr: PriceEntry[];

  constructor(length: number) {
    this.arr = new Array(length);
    console.log("CircularBuffer constructor: ", this.arr.length);
  }

  public push(entry: PriceEntry) {
    this.arr.push(entry);
    this.arr.shift();
  }

  public findRecord(startTime: number, highest: boolean): PriceEntry {
    let record: PriceEntry = this.arr[0];

    this.arr.forEach((entry) => {
      if (highest) {
        if (
          !record ||
          (entry.timestamp >= startTime && entry.price > record.price)
        ) {
          record = entry;
        }
      } else {
        if (
          !record ||
          (entry.timestamp >= startTime && entry.price < record.price)
        ) {
          record = entry;
        }
      }
    });
    return record;
  }
}
