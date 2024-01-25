const { SlashCommandBuilder, EmbedBuilder } = require("discord.js");
const config = require("../../config");
const logger = require("../../../utils/logger");
const User = require("../../../database/models/user");
const UserItem = require("../../../database/models/userItem");

module.exports = {
    data: new SlashCommandBuilder()
        .setName("profile")
        .setDescription(`profile`),
    async execute(interaction) {},
};
