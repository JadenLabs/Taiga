const Sequelize = require("sequelize");
const sequelize = require("../database");

const UserItem = sequelize.define("userItem", {
    id: {
        type: Sequelize.INTEGER,
        primaryKey: true,
        autoIncrement: true,
    },
    itemID: {
        type: Sequelize.INTEGER,
        required: true,
    },
    userID: {
        type: Sequelize.INTEGER,
        required: true,
    },
    quantity: {
        type: Sequelize.INTEGER,
        defaultValue: 1,
    },
});

module.exports = UserItem;
