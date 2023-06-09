import { ChatInputApplicationCommandData, Client, CommandInteraction } from "discord.js";
import { Hello } from "./Hello";

export interface Command extends ChatInputApplicationCommandData {
    run: (client: Client, interaction: CommandInteraction) => void;
}

export const AllCommands: Command[] = [Hello];