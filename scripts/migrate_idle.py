"""Backfill the idle-scaling fields onto existing user docs.

Run once from the project root (env is loaded by importing src.core):

    python scripts/migrate_idle.py

Idempotent: docs already carrying `idleMigrated` are skipped.

Decoupling note: the bean multiplier used to come straight from a user's
goldenBeans count (+25% each). It now comes from the `golden_paws` permanent
upgrade. To preserve existing players' power we grandfather one Golden Paws
level per golden bean they hold, and *keep* their golden beans as spendable
currency (a small thank-you for early supporters).
"""

from src.database.database import database
from src.bot.cogs.shop import get_generator_rate

DEFAULTS = {
    "permanentUpgrades": {},
    "totalBeansEarned": 0,
    "prestiges": 0,
    "achievements": [],
    "generatorRate": 0,
}

migrated = 0
for user_doc in database.users.find({"idleMigrated": {"$ne": True}}):
    inventory = user_doc.get("inventory", {})
    set_fields: dict = {}

    for key, default in DEFAULTS.items():
        if key not in user_doc:
            set_fields[key] = default

    # Grandfather the prestige multiplier into Golden Paws levels
    golden = user_doc.get("goldenBeans", 0)
    perms = user_doc.get("permanentUpgrades", {})
    if golden > 0 and "golden_paws" not in perms:
        perms = {**perms, "golden_paws": golden}
        set_fields["permanentUpgrades"] = perms

    # Lifetime beans is unknown for old accounts; seed it from current balance
    if user_doc.get("totalBeansEarned", 0) < user_doc.get("beans", 0):
        set_fields["totalBeansEarned"] = user_doc.get("beans", 0)

    # Denormalized production rate for the leaderboard
    set_fields["generatorRate"] = get_generator_rate(inventory)
    set_fields["idleMigrated"] = True

    database.users.update_one({"_id": user_doc["_id"]}, {"$set": set_fields})
    migrated += 1

print(f"Migration complete. Updated {migrated} user(s).")
