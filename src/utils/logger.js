const path = require("path");
const pino = require("pino");
const pretty = require("pino-pretty");

const transport = pino.transport({
    targets: [
        {
            target: "pino-pretty",
            options: { colorize: true, translateTime: true },
        },
        {
            target: "pino/file",
            options: { destination: path.join(__dirname, "../logs/log.log") },
        },
    ],
});

const logger = pino(transport);

module.exports = logger;
