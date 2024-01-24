const Sequelize = require("sequelize");
const sequelize = require("../database");

const Item = sequelize.define("item", {
    id: {
        type: Sequelize.INTEGER,
        primaryKey: true,
        autoIncrement: true,
    },
    name: {
        type: Sequelize.STRING,
        required: true,
    },
    description: {
        type: Sequelize.TEXT,
        defaultValue: null,
    },
    emoji: {
        type: Sequelize.STRING,
        defaultValue: null,
        required: false,
    },
});

module.exports = Item;
