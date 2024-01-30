function getRandomValueFromArray(array) {
    const randomIndex = Math.floor(Math.random() * array.length);
    return array[randomIndex];
}

module.exports = { getRandomValueFromArray };
