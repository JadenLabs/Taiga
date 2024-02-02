const path = require("path");
const { SlashCommandBuilder, EmbedBuilder, time } = require("discord.js");
const sharp = require("sharp");
const config = require("../../config");
const logger = require("../../../utils/logger");
const User = require("../../../database/models/user");
const Beans = require("../../../utils/beans");
const { getRandomTaiga } = require("../../../utils/taiga");

module.exports = {
    data: new SlashCommandBuilder().setName("pet").setDescription("Pet Taiga!"),
    async execute(interaction) {
        const waitingEmbed = new EmbedBuilder()
            .setColor(config.colors.neutral)
            .setDescription(
                `## ${config.emojis.loading} Petting Taiga!\nPlease wait a moment while I snap a picture`
            )
            .setFooter({
                text: "This command is under construction, thank you for your patience.",
            });

        await interaction.reply({ embeds: [waitingEmbed] });

        const [userDB, newUserDB] = await User.findOrCreate({
            where: { id: interaction.user.id },
        });

        // Validate lastPet
        const lastPet = new Date(userDB.lastPet);
        const dateNow = new Date();
        const timeDif = Math.floor((dateNow - lastPet) / 1000);

        if (
            interaction.user.id !== config.ids.roc &&
            timeDif < config.cooldowns.pet
        ) {
            // Timestamp
            const cooldownEndTime = Math.floor(
                lastPet.getTime() / 1000 + config.cooldowns.pet
            );
            const whenAvailable = time(cooldownEndTime, "R");

            // Embed
            const cooldownEmbed = new EmbedBuilder()
                .setColor(config.colors.error)
                .setTitle("Sorry,")
                .setDescription(
                    `Taiga is sleeping right now, please come back ${whenAvailable}.`
                );

            // Response
            return interaction.editReply({ embeds: [cooldownEmbed] });
        }

        // Get random beans
        const oldBeans = userDB.beans;
        const { newBeans, beansAdded } = await Beans.giveBeans(
            oldBeans,
            200,
            500
        );

        // Update DB
        const newPets = userDB.pets + 1;
        await userDB.update({
            pets: newPets,
            lastPet: dateNow,
            beans: newBeans,
        });

        // Create pet send embed
        const embed = new EmbedBuilder()
            .setColor(config.colors.primary)
            .setTitle("You have pet Taiga!")
            .setDescription(
                `Taiga has given you some beans!\n${config.emojis.beans} \`+${beansAdded}\``
            )
            .setFields([
                {
                    name: "Stats",
                    value: `${config.emojis.heart} Pets \`${newPets}\`\n${config.emojis.beans} Beans \`${newBeans}\``,
                    inline: true,
                },
            ]);

        // Get the random Taiga image
        const taigaImg = await new Promise((resolve, reject) => {
            getRandomTaiga((err, result) => {
                if (err) {
                    reject(err);
                } else {
                    resolve(result);
                }
            });
        });

        let taigaImgPath = path.join(
            __dirname,
            "../../../assets/taiga",
            taigaImg
        );

        // Chance for smokey to appear
        const smokeyChance = 5000;
        const smokeyRoll = Math.floor(Math.random() * (smokeyChance - 1) + 1);
        if (smokeyRoll === smokeyChance) {
            taigaImgPath = path.join(
                __dirname,
                "../../../assets/other_cats/smokey.jpg"
            );
            logger.info("Overwrite: a wild smokey appeared");
            embed.setFooter({ text: "Wait.. that isn't Taiga " });
        }

        // Log
        logger.info(`Selected taiga: ${taigaImg} - path ${taigaImgPath}`);

        // Resize the image
        const resizedImageBuffer = await sharp(taigaImgPath)
            .resize({ width: 1000, height: 1000 })
            .rotate()
            .toBuffer();

        try {
            embed.setImage(`attachment://${taigaImg}`);
        } catch (err) {
            // Try again
            embed.setImage(`attachment://${taigaImg}`);
        }

        // Reply
        await interaction.editReply({
            embeds: [embed],
            files: [{ attachment: resizedImageBuffer, name: taigaImg }],
        });

        logger.info(
            `Updated ${interaction.user.username}'s (${interaction.user.id}) pet count to ${newPets}`
        );
    },
};
