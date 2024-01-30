const { ButtonBuilder, ButtonStyle, EmbedBuilder } = require("discord.js");
const config = require("../bot/config");
const { sleep } = require("./time");
const { getRandomValueFromArray } = require("./lists");

const ANIMATION_STEPS = 10;

async function fishingAnimation(interaction) {
    const progressBarLength = 20; // Adjust the length of the loading bar
    const progressBarChar = "▓▓"; // Adjust the character used for the loading bar
    const emptyProgressBarChar = "░░"; // Adjust the character used for the empty part of the loading bar

    // Random message
    const randomMessage = await getRandomValueFromArray(config.fishingMessages);

    for (let i = 0; i < ANIMATION_STEPS; i++) {
        // Make progress bar
        const progress = ((i + 1) / ANIMATION_STEPS) * progressBarLength;
        const progressBar = `${progressBarChar.repeat(
            Math.floor(progress)
        )}${emptyProgressBarChar.repeat(
            Math.ceil(progressBarLength - progress)
        )}`;

        // Embed
        const waitEmbed = new EmbedBuilder()
            .setColor(config.colors.invis)
            .setTitle("FISHING...")
            .setDescription(
                `WORK IN PROGRESS, DONT BULLY ME\n\`\`\`${progressBar}\`\`\``
            )
            .setFooter({ text: `${randomMessage}` });

        await interaction.editReply({ embeds: [waitEmbed] });

        await sleep(1000);
    }
}

module.exports = { fishingAnimation };
