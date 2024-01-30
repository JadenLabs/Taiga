const { SlashCommandBuilder, EmbedBuilder, time } = require("discord.js");
const config = require("../../config");
const logger = require("../../../utils/logger");
const { getGlobalPets, getGlobalBeans } = require("../../../utils/stats");
const Stat = require("../../../database/models/stats");
const os = require("os");

module.exports = {
    data: new SlashCommandBuilder()
        .setName("stats")
        .setDescription(`View Taiga's stats!`),
    async execute(interaction) {
        // Defer
        await interaction.deferReply();

        // Get stats
        const [commandsRan, isCommandsRanNew] = await Stat.findOrCreate({
            where: { name: "commandsRan" },
        });

        // System information
        const osInfo = os.type();
        const cpuInfo = os.cpus()[0].model;
        const totalMemory = Math.round(os.totalmem() / (1024 * 1024));

        // Economy stats
        const globalPets = await getGlobalPets();
        const globalBeans = await getGlobalBeans();

        // Bot information
        const uptime = process.uptime();
        const formattedUptime = time(new Date(Date.now() - uptime), "R");
        const guilds = interaction.client.guilds.cache.size;
        const users = interaction.client.users.cache.size;
        const discordjsVersion = require("discord.js").version;
        const botVersion = "1.0.0";

        // Embed
        const statsEmbed = new EmbedBuilder()
            .setColor(config.colors.invis)
            .setTitle("Taiga bot stats")
            .addFields([
                {
                    name: "Bot",
                    value: `- Commands Ran: \`${commandsRan.value}\`
- Started: ${formattedUptime}
- Servers: \`${guilds}\`
- Users (cached): \`${users}\`
- Library: \`Discord.js v${discordjsVersion}\`
- Bot Version: \`${botVersion}\``,
                    inline: true,
                },
                {
                    name: "System",
                    value: `\
- OS: \`${osInfo}\`
- CPU: \`${cpuInfo}\`
- Memory: \`${totalMemory} MB\`
`,
                    inline: true,
                },
                {
                    name: "Economy",
                    value: `\
- Global Pets: \`${globalPets}\`
- Global Beans: \`${globalBeans}\`
`,
                    inline: true,
                },
            ]);

        // Respond
        await interaction.editReply({ embeds: [statsEmbed] });
    },
};
