import Crypto from "./Crypto";



class CryptoManager {
  private static instance: CryptoManager;

  public cryptos: Map<string, Crypto> = new Map<string, Crypto>();
  public currentCryptoList: string[] = ["ETHUSDT", "ZILUSDT", "BTCUSDT", "BNBUSDT", "DOTUSDT", "GLMRUSDT"];
  public surveillanceTimes = [1]

  private constructor() {
    console.log("CryptoManager constructor");

    //INFO: If I wanted to reimplement the config file, I would need to implement it here.
    this.currentCryptoList.forEach((symbol) => {
      this.cryptos.set(symbol, new Crypto(symbol));
    })
  }

  public static getInstance(): CryptoManager {
    if (!CryptoManager.instance) {
      CryptoManager.instance = new CryptoManager();
    }

    return CryptoManager.instance;
  }

  public getCrypto(symbol: string): Crypto {
    const crypto = this.cryptos.get(symbol);
    if (!crypto) {
      throw new Error(`Crypto ${symbol} not found`);
    }
    return crypto;
  }

  public async start() {

  }
}

export default CryptoManager.getInstance();