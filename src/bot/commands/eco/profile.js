const { SlashCommandBuilder, EmbedBuilder } = require("discord.js");
const config = require("../../config");
const logger = require("../../../utils/logger");
const User = require("../../../database/models/user");
const UserItem = require("../../../database/models/userItem");
const { getWhenAvailableTimestamp } = require("../../../utils/cooldowns");
const { getItem, getUserItem } = require("../../../utils/items");

module.exports = {
    data: new SlashCommandBuilder()
        .setName("profile")
        .setDescription(`View a user's profile!`)
        .addUserOption((option) =>
            option
                .setName("user")
                .setDescription("The user to view the profile of")
        ),
    async execute(interaction) {
        // Defer in case operation is slow
        await interaction.deferReply();

        // Load options
        const user =
            (await interaction.options.getUser("user")) || interaction.user;

        // Get database objects
        const [userDB, isUserDBNew] = await User.findOrCreate({
            where: { id: user.id },
        });

        // Load strings
        const userAvatar = await user.avatarURL();
        const whenPetAvailable = userDB.lastPet
            ? await getWhenAvailableTimestamp(
                  userDB.lastPet,
                  config.cooldowns.pet
              )
            : "`Ready`";

        // Embed
        const embed = new EmbedBuilder()
            .setColor(config.colors.invis)
            .setTitle(`${user.username}'s Profile`)
            .setThumbnail(userAvatar)

            .setFields([
                {
                    name: "Stats",
                    inline: true,
                    value: `\
- Pets: \`${userDB.pets}\`
- Beans: \`${userDB.beans}\`
`,
                },
                {
                    name: "Cooldowns",
                    inline: true,
                    value: `\
- Pet: ${whenPetAvailable}
`,
                },
            ])
            .setFooter({ text: "Under construction!" });

        // Check for golden beans
        const goldenBeans = await getItem({ name: "Golden Beans" });
        golden_bean_check: if (goldenBeans) {
            const hasGoldenBeans = await getUserItem(user.id, goldenBeans.id);
            if (!hasGoldenBeans) break golden_bean_check;

            const goldenBeansStr = "`GB Holder`\n";
            embed.setDescription(`${goldenBeansStr}`);
        }

        // Respond
        await interaction.editReply({ embeds: [embed] });
    },
};
