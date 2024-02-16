const Sequelize = require("sequelize");
const sequelize = require("../database");

const Staff = sequelize.define("staff", {
    id: {
        type: Sequelize.STRING,
        primaryKey: true,
    },
    scope: {
        type: Sequelize.INTEGER,
        defaultValue: 0,
    },
    note: {
        type: Sequelize.TEXT,
        defaultValue: null,
    },
});

module.exports = Staff;
