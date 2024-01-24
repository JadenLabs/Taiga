const { Sequelize } = require("sequelize");
const sequelize = require("../database");
const fs = require("fs");
const path = require("path");

const modelsDir = path.join(__dirname, "../models");

console.log(`Syncing Database`);

fs.readdirSync(modelsDir)
    .filter((file) => file.endsWith(".js"))
    .forEach((file) => {
        const model = require(path.join(modelsDir, file));
        // Sync each model to the database
        model.sync({ alter: true });
        console.log(`Synced ${file}`);
    });

console.log(`Synced Database`);
