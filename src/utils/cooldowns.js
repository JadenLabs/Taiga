const { time } = require("discord.js");

async function getWhenAvailableTimestamp(lastUseEpoch, cooldown) {
    const lastUse = new Date(lastUseEpoch);
    const cooldownEndTime = Math.floor(lastUse.getTime() / 1000 + cooldown);
    const whenAvailable = time(cooldownEndTime, "R");
    return whenAvailable;
}

module.exports = { getWhenAvailableTimestamp };
