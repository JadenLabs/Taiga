async function giveBeans(amount, min, max) {
    const randomValue = Math.random() * (max - min) + min;

    const roundedRandomValue = Math.round(randomValue);

    const result = Math.min(Math.max(roundedRandomValue, min), max);

    const finalResult = result + amount;

    return {
        newBeans: finalResult,
        beansAdded: roundedRandomValue,
    };
}

module.exports = {
    giveBeans,
};
