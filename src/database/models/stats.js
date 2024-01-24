const Sequelize = require("sequelize");
const sequelize = require("../database");

const Stat = sequelize.define("stat", {
    name: {
        type: Sequelize.STRING,
        primaryKey: true,
    },
    value: {
        type: Sequelize.INTEGER,
        defaultValue: 0,
    },
});

module.exports = Stat;
