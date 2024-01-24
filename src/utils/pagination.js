const config = require("../bot/config");
const User = require("../database/models/user");
const { EmbedBuilder, Embed } = require("discord.js");

function paginate(array, page_size, page_number) {
    return array.slice(page_number * page_size, (page_number + 1) * page_size);
}

async function getPaginatedUsers(pageNumber, pageSize, sortBy, order) {
    try {
        // Paginate users
        const offset = (pageNumber - 1) * pageSize;
        const limit = pageSize;

        const users = await User.findAll({
            order: [[sortBy, order]],
            offset,
            limit,
        });

        // Get total number of pages
        const pages = Math.ceil((await User.count()) / limit);

        return { users, pages };
    } catch (error) {
        console.error("Error fetching users:", error);
        throw error;
    }
}

async function getUserLeaderboardEmbed(client, page_number, page_size, value) {
    // Get users from database
    const { users: usersArray, pages } = await getPaginatedUsers(
        page_number,
        page_size,
        value,
        "DESC"
    );

    // Format users
    const usersMap = await Promise.all(
        usersArray.map(async (user, index) => {
            ++index;
            const discordUser = await client.users.fetch(user.id);
            const userValue = user[value];

            return `**${index}.** \`  ${userValue}  \` ${discordUser} \`(${discordUser.username})\``;
        })
    );

    // Format strings for display
    const users = usersMap.join("\n");
    const valueToCap = value.charAt(0).toUpperCase() + value.slice(1);

    // Create embed
    const embed = new EmbedBuilder()
        .setColor(config.colors.primary)
        .setTitle(`${valueToCap} Leaderboard!`)
        .setDescription(
            `Here are the current leaders for ${valueToCap}!\n\n${users}`
        )
        .setFooter({ text: `Page ${page_number + 1} of ${pages}` });

    // Return
    return { embed };
}

module.exports = {
    paginate,
    getPaginatedUsers,
    getUserLeaderboardEmbed,
};
