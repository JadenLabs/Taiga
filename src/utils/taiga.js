const fs = require("fs");
const path = require("path");

const TAIGA_IMGS = path.join(__dirname, "../assets/taiga");

function getRandomTaiga(callback) {
    fs.readdir(TAIGA_IMGS, (err, files) => {
        if (err) {
            callback(err, null);
            return;
        }

        // Filter files
        const jpgFiles = files.filter(
            (file) => path.extname(file).toLowerCase() === ".jpg"
        );

        if (jpgFiles.length === 0) {
            callback(null, "No .jpg files found in the directory.");
            return;
        }

        // Choose a random file
        const randomFile =
            jpgFiles[Math.floor(Math.random() * jpgFiles.length)];

        callback(null, randomFile);

        return randomFile;
    });
}

getRandomTaiga((err, result) => {
    if (err) {
        console.error("Error:", err);
    } else {
        // console.log("Randomly selected .jpg file:", result);
    }
});

module.exports = { getRandomTaiga };
