from traceback import print_exc
from discord import app_commands, Interaction, Embed, ButtonStyle, Message
from discord.ext.commands import GroupCog
from discord.ui import Button, View
from src.core import core, logger
from src.bot import Bot
from src.utils.leaderboard import Leaderboard, SortOrder
from functools import partial


class Leaderboards(GroupCog, name="lb", description="Leaderboard commands"):
    """Leaderboards cog"""

    def __init__(self, bot: Bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="pets", description="Shows the pets leaderboard!")
    async def pets(self, ctx: Interaction, page: int = 1):
        """Shows the pets leaderboard!

        Args:
            ctx (Interaction): The command interaction.
            page (int, optional): The page of the leaderboard to view. Defaults to 1.
        """
        try:
            await self.send_leaderboard(ctx, page, "pets")
        except Exception as e:
            print_exc()
            logger.error("An error has occurred:", e)

    @app_commands.command(name="beans", description="Shows the beans leaderboard!")
    async def beans(self, ctx: Interaction, page: int = 1):
        """Shows the pets leaderboard!

        Args:
            ctx (Interaction): The command interaction.
            page (int, optional): The page of the leaderboard to view. Defaults to 1.
        """
        try:
            await self.send_leaderboard(ctx, page, "beans")
        except Exception as e:
            print_exc()
            logger.error("An error has occurred:", e)

    async def send_leaderboard(self, ctx: Interaction, page: int, field: str):
        if not ctx.response.is_done():
            await ctx.response.defer()

        leaderboard = Leaderboard(
            collection_name="users", sort_field=field, sort_order=SortOrder.Desc
        )

        page = max(1, min(page, leaderboard.page_count))

        lb_docs = leaderboard.get_page(page)

        def fmt_docs(doc: dict):
            return f"**{doc['rank']}.** ` {doc[field]} ` <@{doc['_id']}>"

        field_fmt = field.capitalize()

        description = f"Here are the current leaders for {field_fmt}!\n\n" + "\n".join(
            map(fmt_docs, lb_docs)
        )
        footer = f"Page {page} of {leaderboard.page_count}"

        embed = Embed(
            title=f"{field_fmt} Leaderboard!",
            description=description,
            color=core.config.data["colors"]["primary"],
        )
        embed.set_footer(text=footer)

        prev_button = Button(label="Previous", style=ButtonStyle.primary)
        next_button = Button(label="Next", style=ButtonStyle.primary)

        view = View()
        if page > 1:
            view.add_item(prev_button)
        if page < leaderboard.page_count:
            view.add_item(next_button)

        async def prev_callback(interaction: Interaction):
            await self.send_leaderboard(interaction, page - 1, field)

        async def next_callback(interaction: Interaction):
            await self.send_leaderboard(interaction, page + 1, field)

        prev_button.callback = partial(prev_callback)
        next_button.callback = partial(next_callback)

        await ctx.edit_original_response(embed=embed, view=view)


async def setup(bot: Bot):
    await bot.add_cog(Leaderboards(bot))
