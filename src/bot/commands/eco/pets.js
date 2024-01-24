const { SlashCommandBuilder, EmbedBuilder } = require("discord.js");
const config = require("../../config");
const logger = require("../../../utils/logger");
const { getUserLeaderboardEmbed } = require("../../../utils/pagination");

module.exports = {
    data: new SlashCommandBuilder()
        .setName("pets")
        .setDescription(`View the pets leaderboard!`),
    async execute(interaction) {
        // Defer as operation is slow
        await interaction.deferReply();

        // Get embed
        const initialPageIndex = 0;
        const pageSize = 10;
        const { embed } = await getUserLeaderboardEmbed(
            interaction.client,
            initialPageIndex,
            pageSize,
            "pets"
        );

        // Reply
        await interaction.editReply({ embeds: [embed] });
    },
};
