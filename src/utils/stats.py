from src.database.database import database


def increment_cmds_ran(n: int = 1):
    cmds_stat_doc = database.stats.find_one({"name": "commands_ran"})
    if cmds_stat_doc is None:
        database.stats.insert_one({"name": "commands_ran", "value": n})
        return n

    new_cmds = cmds_stat_doc["value"] + n

    database.stats.update_one({"name": "commands_ran"}, {"$set": {"value": new_cmds}})
    return new_cmds
