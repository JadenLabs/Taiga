"""Retroactively check every user for achievements and DM them a summary.

Runs inside a temporary bot login so it can send DMs. Achievement granting
reuses `check_achievements` (idempotent - re-running won't double-award), then
each qualifying user is DMed the list of achievements they hold and anything
newly awarded in this pass. DMs are paced by `--delay` to dodge rate limits.

Run from the project root:

    python scripts/award_achievements.py [--delay 1.5] [-e .env] [-c config.toml]

Test against a single id (the lead dev) without touching anyone else:

    python scripts/award_achievements.py --test
"""

import sys
import argparse
import asyncio

# The script defines its own flags, but importing src.core runs get_args()
# (strict argparse) at import time. Parse ours first, then hand src.core a
# clean argv containing only the -e/-c it understands.
_parser = argparse.ArgumentParser(description=__doc__)
_parser.add_argument(
    "--test", action="store_true", help="Only process the lead-dev id (for testing DMs)"
)
_parser.add_argument(
    "--delay",
    type=float,
    default=1.5,
    help="Seconds to wait between DMs (rate-limit cushion)",
)
_parser.add_argument("-e", "--env", type=str, help="The env file to use")
_parser.add_argument("-c", "--config", type=str, help="The config file to use")
ARGS = _parser.parse_args()

_core_argv = [sys.argv[0]]
if ARGS.env:
    _core_argv += ["-e", ARGS.env]
if ARGS.config:
    _core_argv += ["-c", ARGS.config]
sys.argv = _core_argv

import os
import discord
from src.core import core, logger
from src.database.database import database
from src.utils.user import find_user_or_default
from src.bot.cogs.shop import check_achievements, ACHIEVEMENTS

TEST_ID = "1027380375028244551"  # lead dev - used by --test
ACH_META = {a["name"]: a for a in ACHIEVEMENTS}


def build_summary_embed(user_doc: dict, newly: list[dict]) -> discord.Embed:
    """A DM summarising the user's unlocked achievements and any new awards."""
    golden_emoji = core.config.data["emojis"]["golden_beans"]
    bot_name = core.config.data["bot"]["name"]
    unlocked = user_doc.get("achievements", [])
    new_names = {a["name"] for a in newly}

    lines = []
    for name in unlocked:
        ach = ACH_META.get(name)
        if ach is None:
            continue  # an achievement that no longer exists in config
        title = name.replace("_", " ").title()
        reward = ach.get("reward_golden", 0)
        reward_str = f" · `+{reward}` {golden_emoji}" if reward else ""
        new_tag = " ✨ **NEW!**" if name in new_names else ""
        lines.append(
            f"{ach['emoji']} **{title}** - {ach['description']}{reward_str}{new_tag}"
        )

    body = "\n".join(lines) if lines else "No achievements yet - keep petting Taiga!"
    description = f"You've unlocked **{len(lines)}/{len(ACHIEVEMENTS)}** achievements!\n\n{body}\n\n-# Achievements are a new addition to Taiga, this is a one-time message - don't worry"
    if newly:
        gained = sum(a.get("reward_golden", 0) for a in newly)
        gained_str = f" · `+{gained}` {golden_emoji} awarded!" if gained else "!"
        description += (
            f"\n\n✨ **{len(newly)} new** unlocked in this update{gained_str}"
        )

    embed = discord.Embed(
        color=core.config.data["colors"]["secondary"],
        title=f"🏆 Your {bot_name} Achievements",
        description=description,
    )

    return embed


async def run(client: discord.Client) -> None:
    if ARGS.test:
        logger.info(f"TEST MODE - only processing {TEST_ID}")
        find_user_or_default(TEST_ID)  # make sure the doc exists
        user_ids = [TEST_ID]
    else:
        user_ids = [doc["_id"] for doc in database.users.find({}, {"_id": 1})]
        logger.info(f"Processing {len(user_ids)} user(s)")

    sent = skipped = failed = 0
    for uid in user_ids:
        user_doc = database.users.find_one({"_id": str(uid)})
        if user_doc is None:
            continue

        # Grant any achievements they now qualify for (idempotent)
        newly = check_achievements(uid, user_doc)
        user_doc = database.users.find_one({"_id": str(uid)})  # re-read post-grant

        # Skip people with nothing to celebrate (always DM in test mode)
        if not user_doc.get("achievements") and not ARGS.test:
            skipped += 1
            continue

        try:
            user = await client.fetch_user(int(uid))
            await user.send(embed=build_summary_embed(user_doc, newly))
            sent += 1
            logger.info(f"DM sent to {uid} ({len(newly)} new)")
        except discord.Forbidden:
            failed += 1
            logger.debug(f"Could not DM {uid} (DMs closed / no shared guild)")
        except discord.NotFound:
            failed += 1
            logger.debug(f"User {uid} not found")
        except discord.HTTPException as e:
            failed += 1
            logger.error(f"HTTP error DMing {uid}: {e}")

        # Cooldown between DMs to stay under Discord's rate limits
        await asyncio.sleep(ARGS.delay)

    logger.info(f"Done. Sent={sent} Skipped={skipped} Failed={failed}")


def main() -> None:
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    started = False

    @client.event
    async def on_ready():
        nonlocal started
        if started:  # on_ready can fire again on reconnect
            return
        started = True
        logger.info(f"Logged in as {client.user} - starting achievement pass")
        try:
            await run(client)
        finally:
            await client.close()

    client.run(os.getenv("BOT_TOKEN"))


if __name__ == "__main__":
    main()
