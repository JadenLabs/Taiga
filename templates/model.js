const Sequelize = require("sequelize");
const sequelize = require("../database");

const Model = sequelize.define("model", {
    id: {
        type: Sequelize.STRING,
        primaryKey: true,
    },
});

module.exports = Model;
