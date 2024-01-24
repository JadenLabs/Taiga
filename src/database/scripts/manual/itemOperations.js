const User = require("../../models/user");
const Item = require("../../models/item");
const UserItem = require("../../models/userItem");

async function createItem(itemData) {
    const itemDB = await Item.create(itemData);

    console.log(itemDB);
}

createItem({
    name: "Bass",
    description: "A basic fish - can be fed to Taiga for 1 energy point.",
});

async function updateItem(id, data) {
    const itemDB = await User.update({ data }, { where: { id } });

    console.log(itemDB);
}

async function giveItemInMass(id) {
    const users = await User.findAll();

    for (const user of users) {
        const [userItem, userItemIsNew] = await UserItem.findOrCreate({
            where: { itemID: id, userID: user.id },
        });

        // if (!userItemIsNew)
        //     await userItem.update({ quantity: userItem.quantity + 1 });
    }

    console.log(`items updated`);
}

// giveItemInMass(1);
