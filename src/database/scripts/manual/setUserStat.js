const User = require("../../models/user");

async function setStat(userID, stat, value) {
    const userDB = await User.update(
        { [stat]: value },
        { where: { id: userID } }
    );

    console.log(userDB);
}

// setStat("", "", 0);
