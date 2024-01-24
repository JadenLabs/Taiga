const { SlashCommandBuilder, EmbedBuilder } = require("discord.js");
const config = require("../../config");
const logger = require("../../../utils/logger");
const UserItem = require("../../../database/models/userItem");

module.exports = {
    data: new SlashCommandBuilder()
        .setName("fish")
        .setDescription(`Fish for... fish!`),
    async execute(interaction) {
        // TODO: add functionality

        await interaction.reply({
            content: "Under Construction",
            ephemeral: true,
        });
    },
};
