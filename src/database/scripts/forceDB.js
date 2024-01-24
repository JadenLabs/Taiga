const { Sequelize } = require("sequelize");
const sequelize = require("../database");

const model = "";
const db = require(`../models/${model}`);

// ! Wipes ALL data for the Model
console.log(`Forcing ${model}, all data will be wiped.`);
db.sync({ force: true });
console.log(`Forced ${model}, all data was wiped.`);
