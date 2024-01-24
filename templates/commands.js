const { SlashCommandBuilder, EmbedBuilder } = require("discord.js");
const config = require("../../config");
const logger = require("../../../utils/logger");

module.exports = {
    data: new SlashCommandBuilder().setName("cmd").setDescription(`cmd`),
    async execute(interaction) {
        // ...
    },
};
