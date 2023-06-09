import { Client } from "discord.js";
import { AllCommands } from "../commands/Command";

export default (client: Client): void => {
  client.on("ready", async () => {
    if (!client.user || !client.application) {
      return;
    }

    await client.application.commands.set(AllCommands);

    console.log(`${client.user.username} is online`);
  });
};
