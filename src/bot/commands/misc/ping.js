const { SlashCommandBuilder, EmbedBuilder } = require("discord.js");
const config = require("../../config");
const logger = require("../../../utils/logger");

module.exports = {
    data: new SlashCommandBuilder()
        .setName("ping")
        .setDescription(`Pings Taiga!`),
    async execute(interaction) {
        // Grab client latency
        const latency = Math.abs(Date.now() - interaction.createdAt);

        // Make embed
        const pingReply = new EmbedBuilder()
            .setColor(config.colors.primary)
            .setTitle("Pong 🏓")
            .setDescription(`Latency: \`${latency}\`ms`);

        // Reply
        await interaction.reply({ embeds: [pingReply] });

        logger.info(`Res ping -> latency of ${latency}ms`);
    },
};
