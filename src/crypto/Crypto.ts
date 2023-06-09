
type Entry = {
  timestamp: number;
  price: number;
}

export default class Crypto {
  private symbol: string;

  //records for the last x hours
  private records: Map<number, Entry> = new Map<number, Entry>();
  //timestamp to entry
  private prices: Map<number, Entry> = new Map<number, Entry>();

  public constructor(symbol: string) {
    this.symbol = symbol;
  }

  public receivedNewKline(kline: any) {
    console.log(this.symbol + " | receivedNewKline: ", kline);
    // const entry: Entry = {
    //   timestamp: kline.startTime,
    //   price: kline.,
    // }
  }
}
