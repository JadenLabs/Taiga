const { key: botKey } = require("./keys/bot_key.json");

class Config {
    constructor() {
        this.keys = {
            botKey,
        };

        this.botID = "1192973252205752430";

        this.colors = {
            primary: "#E7C7EF",
            secondary: "#F7DB69",
            neutral: "#C4B7C8",
            success: "#68BB6C",
            error: "#EF5552",
            invis: "#2B2D31",
        };

        this.emojis = {
            loading: "<a:loading:1193049795082858597>",
            beans: "🫘",
            heart: "<:lavenderheart:1190469444133208084>",
        };

        // Cooldowns in seconds
        this.cooldowns = {
            pet: 43200,
        };

        this.ids = {
            roc: "1027380375028244551",
        };

        this.fishingMessages = [
            "How much grass have you touched this week?",
            "You're petting Taiga daily, right??",
            "Hail Taiga.",
        ];
    }
}

const config = new Config();

module.exports = config;
