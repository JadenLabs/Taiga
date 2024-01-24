const config = require("./config");
const fs = require("node:fs");
const path = require("node:path");
const { Client, Collection, GatewayIntentBits } = require("discord.js");
const logger = require("../utils/logger");

logger.info("Starting up");

const client = new Client({ intents: [GatewayIntentBits.Guilds] });

// Load commands
logger.info("Loading commands");
client.commands = new Collection();
const foldersPath = path.join(__dirname, "commands");
const commandFolders = fs.readdirSync(foldersPath);

for (const folder of commandFolders) {
    const commandsPath = path.join(foldersPath, folder);
    const commandFiles = fs
        .readdirSync(commandsPath)
        .filter((file) => file.endsWith(".js"));
    for (const file of commandFiles) {
        const filePath = path.join(commandsPath, file);
        const command = require(filePath);
        if ("data" in command && "execute" in command) {
            client.commands.set(command.data.name, command);
        } else {
            logger.warn(
                `Command ${filePath} missing required "data" or "execute" property`
            );
        }
    }
}

// Load buttons
logger.info("Loading buttons");
client.buttons = new Map();
const buttonsPath = path.join(__dirname, "./components/buttons");
const buttonFiles = fs
    .readdirSync(buttonsPath)
    .filter((file) => file.endsWith(".js"));

for (const file of buttonFiles) {
    const button = require(`${buttonsPath}/${file}`);
    client.buttons.set(button.data.customId, button);
}

// Load modals
logger.info("Loading modals");
client.modals = new Map();
const modalsPath = path.join(__dirname, "./components/modals");
const modalFiles = fs
    .readdirSync(modalsPath)
    .filter((file) => file.endsWith(".js"));

for (const file of modalFiles) {
    const model = require(`${modalsPath}/${file}`);
    client.modals.set(model.data.customId, model);
}

// Handle events
logger.info("Loading events");
const eventsPath = path.join(__dirname, "events");
const eventFiles = fs
    .readdirSync(eventsPath)
    .filter((file) => file.endsWith(".js"));

for (const file of eventFiles) {
    const filePath = path.join(eventsPath, file);
    const event = require(filePath);
    if (event.once) {
        client.once(event.name, (...args) => event.execute(...args));
    } else {
        client.on(event.name, (...args) => event.execute(...args));
    }
}

logger.info("Logging into Discord");
client.login(config.keys.botKey);
