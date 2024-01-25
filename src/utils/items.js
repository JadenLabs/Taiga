const Item = require("../database/models/item");
const UserItem = require("../database/models/userItem");

async function getItem(itemQuery) {
    const item = await Item.findOne({ where: itemQuery });
    return item;
}

async function getUserItem(userID, itemID) {
    const userItem = await UserItem.findOne({ where: { userID, itemID } });
    return userItem;
}

module.exports = { getItem, getUserItem };
