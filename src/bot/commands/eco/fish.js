const { SlashCommandBuilder, EmbedBuilder } = require("discord.js");
const config = require("../../config");
const logger = require("../../../utils/logger");
const Item = require("../../../database/models/item");
const UserItem = require("../../../database/models/userItem");
const { fishingAnimation } = require("../../../utils/fishing");

module.exports = {
    data: new SlashCommandBuilder()
        .setName("fish")
        .setDescription(`Fish for... fish!`),
    async execute(interaction) {
        // Defer as cmd can be intensive
        await interaction.deferReply();

        // Run animation
        await fishingAnimation(interaction);

        // Give user fish
        const bass = await Item.findOne({ where: { name: "Bass" } });
        const fish = bass; // TODO: add a fish pool and randomize

        const [fishItem, fishItemIsNew] = await UserItem.findOrCreate({
            where: { itemID: fish.id, userID: interaction.user.id },
        });

        if (!fishItemIsNew)
            await fishItem.update({ quantity: fishItem.quantity + 1 });

        // Embed
        const fishEmbed = new EmbedBuilder()
            .setColor(config.colors.primary)
            .setTitle("You have caught a fish!").setDescription(`\
You have caught a ${fish.name}!
You now have \`${fishItem.quantity}\` ${fish.name} ${config.emojis.fish}`);

        // Respond
        await interaction.editReply({ embeds: [fishEmbed] });
    },
};
