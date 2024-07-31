import requests
from datetime import datetime
from traceback import print_exc
from discord import app_commands, Interaction, Embed
from discord.ext.commands import Cog
from src.core import core, logger
from src.bot import Bot


def format_commit(commit: dict):
    # Get values from the dict
    hash = commit.get("sha")
    commit_data = commit.get("commit")
    message = commit_data.get("message")
    author = commit_data.get("author")["name"]
    date = commit_data.get("author")["date"]
    url = commit.get("html_url")

    # Assert because we *love* error catching
    assert hash, "Hash not found"
    assert message, "Message not found"
    assert author, "Author name not found"
    assert date, "Author date not found"
    assert url, "Url not found"

    # Do some formatting after assertion
    hash = hash[:8]
    date_format = "%Y-%m-%dT%H:%M:%SZ"
    date = int(datetime.strptime(date, date_format).timestamp())

    return {
        "hash": hash,
        "message": message,
        "author": author,
        "date": date,
        "url": url,
    }


class Info(Cog):
    """Information cog"""

    def __init__(self, bot: Bot):
        self.bot = bot

    @app_commands.command(
        name="changelog",
        description=f"View {core.config.data['bot']['name']}'s changelog",
    )
    async def changelog(self, ctx: Interaction):
        """Sends the most recent changes to the bot's github"""
        await ctx.response.defer(ephemeral=True)

        # Github info
        github_owner = core.config.data["github"]["owner"]
        github_name = core.config.data["github"]["name"]
        github_api_url = (
            f"https://api.github.com/repos/{github_owner}/{github_name}/commits"
        )

        # Get recent changes via http
        params = {"per_page": core.config.data["github"]["commits_per_page"]}
        response = requests.get(github_api_url, params=params)

        # Format commits payload
        commits = None
        try:
            commits_dict: list[dict] = response.json()
            commits_fmt = list(map(format_commit, commits_dict))
            commits = commits_fmt
        except Exception as e:
            print_exc()
            logger.error(f"Error formatting commits: {e}")
            raise e

        # Create embed
        embed = Embed(
            color=core.config.data["colors"]["primary"], title="Recent changes:"
        )

        # Format commits into fields
        for index, commit in enumerate(commits, start=1):
            data = {
                "name": f"{index}. #{commit['hash']}",
                "value": f"""\
<t:{commit["date"]}:R> by {commit["author"]}
**Message**:
```{commit["message"]}```
-# [View on GitHub]({commit["url"]})
""",
            }
            embed.add_field(**data)

        await ctx.edit_original_response(embed=embed)


async def setup(bot: Bot):
    await bot.add_cog(Info(bot))
