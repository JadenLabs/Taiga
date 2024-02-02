const { SlashCommandBuilder, EmbedBuilder, time } = require("discord.js");
const config = require("../../config");
const logger = require("../../../utils/logger");
const axios = require("axios");

module.exports = {
    data: new SlashCommandBuilder()
        .setName("phangelog")
        .setDescription(`View Taiga's changelog`),
    async execute(interaction) {
        const owner = "JadenLabs";
        const repo = "Taiga";

        const apiUrl = `https://api.github.com/repos/${owner}/${repo}/commits`;

        try {
            const response = await axios.get(apiUrl, {
                params: {
                    per_page: 10,
                },
            });

            const commits = response.data.map((commit) => {
                return {
                    hash: commit.sha.substr(0, 7),
                    message: commit.commit.message,
                    author: commit.commit.author.name,
                    date: commit.commit.author.date,
                    url: commit.html_url,
                };
            });

            const fields = commits.map((commit, index) => ({
                name: `${index + 1}. #${commit.hash}`,
                value: `${time(new Date(commit.date), "R")} by ${
                    commit.author
                }\n**Message:**\n\`\`\`${
                    commit.message
                }\`\`\`\n[View on GitHub](${commit.url})`,
            }));

            const changelogEmbed = new EmbedBuilder()
                .setColor(config.colors.invis)
                .setTitle(`Last 10 Commits - ${owner}/${repo}`)
                .addFields(fields);

            await interaction.reply({
                embeds: [changelogEmbed],
                ephemeral: true,
            });
        } catch (error) {
            console.error(error);
            await interaction.reply({
                content:
                    "Error fetching commits. Please check if the repository exists and is public.",
                ephemeral: true,
            });
        }
    },
};
