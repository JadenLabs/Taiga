const { ButtonBuilder, ButtonStyle, EmbedBuilder } = require("discord.js");
const config = require("../bot/config");
const { sleep } = require("./time");
const { getRandomValueFromArray } = require("./lists");

const ANIMATION_STEPS = 5;

async function fishingAnimation(interaction) {
    const progressBarLength = 5;
    const progressBarChar = config.emojis.BMF;
    const emptyProgressBarChar = config.emojis.BME;

    // Random message
    const randomMessage = await getRandomValueFromArray(config.fishingMessages);

    for (let i = 0; i < ANIMATION_STEPS; i++) {
        // Make progress bar
        const endEmoji =
            i == ANIMATION_STEPS - 1 ? config.emojis.BRF : config.emojis.BRE;
        const progress = ((i + 1) / ANIMATION_STEPS) * progressBarLength;
        const progressBar = `${config.emojis.BLF}${progressBarChar.repeat(
            Math.floor(progress)
        )}${emptyProgressBarChar.repeat(
            Math.ceil(progressBarLength - progress)
        )}${endEmoji}`;

        // Embed
        const waitEmbed = new EmbedBuilder()
            .setColor(config.colors.primary)
            .setTitle("Fishing...")
            .setDescription(
                `WORK IN PROGRESS, DONT BULLY ME\n## ${progressBar}`
            )
            .setFooter({ text: `${randomMessage}` });

        await interaction.editReply({ embeds: [waitEmbed] });

        await sleep(1000);
    }
}

module.exports = { fishingAnimation };
