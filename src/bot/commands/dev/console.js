const { SlashCommandBuilder, EmbedBuilder } = require("discord.js");
const config = require("../../config");
const logger = require("../../../utils/logger");
const Staff = require("../../../database/models/staff");

async function echo(interaction, text) {
    const echoEmbed = new EmbedBuilder()
        .setColor(config.colors.invis)
        .setDescription(`\`\`\`${text}\`\`\``);

    await interaction.reply({ embeds: [echoEmbed], ephemeral: true });
}

async function addStaff(interaction, args) {
    const [id, scope, ...noteArr] = args;
    const note = noteArr ? noteArr.join(" ") : "No note added.";

    const staffDB = await Staff.findOrCreate({ where: { id, scope, note } });

    const echoEmbed = new EmbedBuilder().setColor(config.colors.invis)
        .setDescription(`\
        Added staff ${id} with scope ${scope}`);

    await interaction.reply({ embeds: [echoEmbed] });
}

module.exports = {
    data: new SlashCommandBuilder()
        .setName("console")
        .setDescription(`dev console, don't touch or I erase your stuff`)
        .addStringOption((option) =>
            option
                .setName("input")
                .setDescription("console input")
                .setRequired(true)
        ),
    async execute(interaction) {
        // Get options
        const input = await interaction.options.getString("input");

        // Misc
        if (interaction.user.id === "966201975798636624") {
            return interaction.reply({
                content:
                    "Penny what are you doing, I knew that you'd run this despite the warning lmao",
                ephemeral: true,
            });
        }

        // Check if staff
        const staffDB = await Staff.findOne({
            where: { id: interaction.user.id },
        });
        if (!staffDB) {
            return interaction.reply({
                content:
                    "Beans and pets reset...\nCurrent values:\n- Beans: `0`\n- Pets: `0`",
                ephemeral: true,
            });
        }

        // Parse
        const [command, ...args] = input.split(" ");

        // Handle commands
        switch (command) {
            case "addStaff":
                return addStaff(interaction, args);
            case "echo":
                await interaction.reply({ content: "ok", ephemeral: true });
                return interaction.channel.send(args.join(" "));
            default:
                return echo(interaction, input);
        }
    },
};
