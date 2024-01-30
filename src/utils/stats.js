const User = require("../database/models/user");

async function getGlobalPets() {
    try {
        const userRecords = await User.findAll();

        const totalPets = userRecords.reduce((sum, userRecord) => {
            const petsValue = parseFloat(userRecord.pets);
            return isNaN(petsValue) ? sum : sum + petsValue;
        }, 0);

        return totalPets;
    } catch (error) {
        console.error("Error fetching user records:", error);
    }
}

async function getGlobalBeans() {
    try {
        const userRecords = await User.findAll();

        const totalBeans = userRecords.reduce((sum, userRecord) => {
            const beansValue = parseFloat(userRecord.beans);
            return isNaN(beansValue) ? sum : sum + beansValue;
        }, 0);

        return totalBeans;
    } catch (error) {
        console.error("Error fetching user records:", error);
    }
}

module.exports = { getGlobalPets, getGlobalBeans };
