import os
from discord import app_commands, Interaction, Embed, ButtonStyle
from discord.ext.commands import Cog
from discord.ui import View, Button
from src.core import core, logger
from src.bot import Bot

ROOT_DIR = os.path.dirname(os.path.abspath("__main__"))
LEGAL_DIR = os.path.join(ROOT_DIR, "legal")
PAGE_LIMIT = 3800  # safely under Discord's 4096-char embed description cap


def load_legal(filename: str) -> str | None:
    """Read a legal markdown file fresh each call so edits take effect live."""
    path = os.path.join(LEGAL_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        logger.error(f"Could not read legal file {path}: {e}")
        return None


def paginate(text: str, limit: int = PAGE_LIMIT) -> list[str]:
    """Split text into embed-sized pages on line boundaries."""
    pages: list[str] = []
    current = ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > limit and current:
            pages.append(current)
            current = ""
        current += line
    if current.strip():
        pages.append(current)
    return pages or ["*(empty document)*"]


class LegalView(View):
    def __init__(self, title: str, pages: list[str], page: int = 0):
        super().__init__(timeout=300)
        self.title = title
        self.pages = pages
        self.page = page
        if len(pages) > 1:
            self.add_item(LegalButton("◀ Previous", -1, disabled=page <= 0))
            self.add_item(LegalButton("Next ▶", 1, disabled=page >= len(pages) - 1))

    def embed(self) -> Embed:
        embed = Embed(
            color=core.config.data["colors"]["primary"],
            title=self.title,
            description=self.pages[self.page],
        )
        if len(self.pages) > 1:
            embed.set_footer(text=f"Page {self.page + 1}/{len(self.pages)}")
        return embed


class LegalButton(Button):
    def __init__(self, label: str, delta: int, disabled: bool):
        super().__init__(label=label, style=ButtonStyle.primary, disabled=disabled)
        self.delta = delta

    async def callback(self, interaction: Interaction):
        view: LegalView = self.view
        new_page = max(0, min(view.page + self.delta, len(view.pages) - 1))
        new_view = LegalView(view.title, view.pages, new_page)
        await interaction.response.edit_message(embed=new_view.embed(), view=new_view)


class Legal(Cog):
    """Terms of Service and Privacy Policy"""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def _send_doc(self, ctx: Interaction, filename: str, title: str):
        text = load_legal(filename)
        if text is None:
            embed = Embed(
                color=core.config.data["colors"]["error"],
                description="That document is currently unavailable. Please try again later.",
            )
            return await ctx.response.send_message(embed=embed, ephemeral=True)

        pages = paginate(text)
        view = LegalView(title, pages)
        await ctx.response.send_message(
            embed=view.embed(),
            view=view if len(pages) > 1 else None,
            ephemeral=True,
        )

    @app_commands.command(name="terms", description="View Taiga's Terms of Service")
    async def terms(self, ctx: Interaction):
        await self._send_doc(ctx, "terms_of_service.md", "📜 Taiga - Terms of Service")

    @app_commands.command(name="privacy", description="View Taiga's Privacy Policy")
    async def privacy(self, ctx: Interaction):
        await self._send_doc(ctx, "privacy_policy.md", "🔒 Taiga - Privacy Policy")


async def setup(bot: Bot):
    await bot.add_cog(Legal(bot))
