const { SlashCommandBuilder, EmbedBuilder } = require("discord.js");
const config = require("../../config");
const logger = require("../../../utils/logger");
const { privacyPolicy } = require("../../../utils/messages");

module.exports = {
    data: new SlashCommandBuilder()
        .setName("privacy")
        .setDescription(`View Taiga's privacy policy!`),
    async execute(interaction) {
        const privacyEmbed = new EmbedBuilder()
            .setColor(config.colors.invis)
            .setDescription(privacyPolicy);

        await interaction.reply({ embeds: [privacyEmbed], ephemeral: true });
    },
};
