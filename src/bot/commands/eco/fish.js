const { SlashCommandBuilder, EmbedBuilder } = require("discord.js");
const config = require("../../config");
const logger = require("../../../utils/logger");
const UserItem = require("../../../database/models/userItem");
const { fishingAnimation } = require("../../../utils/fishing");

module.exports = {
    data: new SlashCommandBuilder()
        .setName("fish")
        .setDescription(`Fish for... fish!`),
    async execute(interaction) {
        await interaction.deferReply();

        await fishingAnimation(interaction);
    },
};
