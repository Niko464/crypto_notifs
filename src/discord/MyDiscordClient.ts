import { Channel, ChannelType, Client, Guild } from "discord.js";
import interactionCreate from "../listeners/interactionCreate";
import ready from "../listeners/ready";
import CryptoManager from "../crypto/CryptoManager";
const dotenv = require("dotenv");

dotenv.config();

const DISCORD_TOKEN = process.env.DISCORD_TOKEN || "";
const CONTROL_CHANNEL_ID = process.env.CONTROL_CHANNEL_ID || "";
const DISCORD_GUILD_ID = process.env.DISCORD_GUILD_ID || "";

if (!DISCORD_TOKEN || !CONTROL_CHANNEL_ID) {
  console.error("Something in the .env is missing (MyDiscordClient)");
  process.exit(1);
}

class MyDiscordClient {
  private static instance: MyDiscordClient;
  public discordClient: Client;

  private guild: Guild | undefined;
  private controlChannel: Channel | undefined;
  private cryptoChannels: Map<string, Channel> = new Map<string, Channel>();

  private constructor() {
    console.log("MyDiscordClient constructor");
    this.discordClient = new Client({
      intents: [],
    });
    ready(this.discordClient);
    interactionCreate(this.discordClient);
    //TODO: check if works (need to await and store new client normally)
  }

  public static getInstance(): MyDiscordClient {
    if (!MyDiscordClient.instance) {
      MyDiscordClient.instance = new MyDiscordClient();
    }

    return MyDiscordClient.instance;
  }

  public async start() {
    console.log("Discord client is starting...");
    await this.discordClient.login(DISCORD_TOKEN);
    //Loading guild
    await this.discordClient.guilds
      .fetch(DISCORD_GUILD_ID)
      .then(async (guild: Guild) => {
        this.guild = guild;
      })
      .catch((err) => {
        console.error(err);
        console.error("Guild not found: ", DISCORD_GUILD_ID);
        process.exit(1);
      });
    //Loading control channel
    await this.discordClient.channels
      .fetch(CONTROL_CHANNEL_ID)
      .then((channel: Channel | null) => {
        if (!channel) {
          console.error("Control channel not found");
          return;
        }
        this.controlChannel = channel;
      });

    if (!this.guild) {
      console.error("No guild... Guild not found ?");
      process.exit(1);
    }
    //Loading all the channels
    await this.guild.channels.fetch().then((channels) => {
      CryptoManager.currentCryptoList.forEach((symbol) => {
        const channel = channels.find(
          (item) => item && item.name === symbol.toLocaleLowerCase()
        );
        if (!channel) {
          console.error(`Channel ${symbol} not found`);
          process.exit(1);
        }
        this.cryptoChannels.set(symbol, channel);
      });
    });
    console.log("Discord client is ready");
  }

  public sendSystemMessage(msg: string) {
    if (
      !this.controlChannel ||
      this.controlChannel.type !== ChannelType.GuildText
    ) {
      console.error("Control channel not found or not a text channel");
      return;
    }
    this.controlChannel.send(msg);
  }

  public sendRecordmessage(
    symbol: string,
    time: number,
    price: number,
    high: boolean
  ) {
    if (!this.cryptoChannels.has(symbol)) {
      console.error(`Channel ${symbol} not found`);
      return;
    }
    const channel = this.cryptoChannels.get(symbol);
    if (!channel || channel.type !== ChannelType.GuildText) {
      console.error(`Channel ${symbol} not found or not a text channel`);
      return;
    }
    channel
      .send(symbol + ` --> ${time}h New ${high ? "high" : "low"}: ${price}`)
      .catch((err) => {
        console.error(`Error sending message to channel ${symbol}`, err);
      });
  }
}

export default MyDiscordClient.getInstance();
