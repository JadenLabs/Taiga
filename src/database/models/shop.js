const Sequelize = require("sequelize");
const sequelize = require("../database");

const Shop = sequelize.define("shop", {
    id: {
        type: Sequelize.INTEGER,
        primaryKey: true,
        autoIncrement: true,
    },
    itemID: {
        type: Sequelize.INTEGER,
        foreignKey: true,
    },
    price: {
        type: Sequelize.INTEGER,
        required: true,
    },
    value: {
        type: Sequelize.INTEGER,
        required: true,
    },
    type: {
        type: Sequelize.STRING,
        defaultValue: null,
    },
});

module.exports = Shop;
