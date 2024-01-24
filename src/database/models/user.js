const Sequelize = require("sequelize");
const sequelize = require("../database");

const User = sequelize.define("user", {
    id: {
        type: Sequelize.STRING,
        primaryKey: true,
    },
    pets: {
        type: Sequelize.INTEGER,
        defaultValue: 0,
    },
    lastPet: {
        type: Sequelize.DATE,
        defaultValue: null,
    },
    beans: {
        type: Sequelize.INTEGER,
        defaultValue: 0,
    },
});

module.exports = User;
