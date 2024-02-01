const { SlashCommandBuilder, EmbedBuilder } = require("discord.js");
const config = require("../../config");
const logger = require("../../../utils/logger");

module.exports = {
    data: new SlashCommandBuilder()
        .setName("bully")
        .setDescription(`bully roc`),
    async execute(interaction) {
        // Get Roc
        const roc = await interaction.client.users.fetch(config.ids.roc);
        const rocDMs = await roc.createDM();

        // Embed
        const wompEmbed = new EmbedBuilder()
            .setColor(config.colors.primary)
            .setDescription(`${interaction.user} hahahahahaha loser`);

        await rocDMs.send({ embeds: [wompEmbed] });

        // Respond
        await interaction.reply({
            content: `${roc} has been bullied in his dms.`,
            ephemeral: true,
        });
    },
};
