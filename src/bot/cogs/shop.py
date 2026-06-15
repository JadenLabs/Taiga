import random
from datetime import datetime, timezone
from discord import app_commands, Interaction, Embed, SelectOption, ButtonStyle
from discord.ext.commands import Cog
from discord.ui import Select, View, Button
from pymongo import ReturnDocument
from src.core import core
from src.bot import Bot
from src.database.database import database
from src.utils.user import find_user_or_default

MIN_COOLDOWN = 3600  # 1 hour floor regardless of items
SELL_RATE = 0.8

CATEGORY_ORDER = [
    ("boosts", "Boosts"),
    ("generators", "Generators"),
    ("generator_upgrades", "Generator Upgrades"),
    ("consumables", "Consumables"),
    ("cosmetics", "Cosmetics"),
]


class Item:
    def __init__(self, data: dict):
        self.name: str = data["name"]
        self.description: str = data["description"]
        self.cost: int = data["cost"]
        self.ownership_limit: int = data.get("ownership_limit", 0)
        self.emoji: str = data.get("emoji", "🔹")
        self.cooldown_reduction: int = data.get("cooldown_reduction", 0)
        self.category: str = data.get("category", "boosts")
        self.beans_per_hour: int = data.get("beans_per_hour", 0)
        self.price_growth: float = data.get("price_growth", 1.0)
        self.bean_bonus: float = data.get("bean_bonus", 0.0)
        # Generator-upgrade fields (category == "generator_upgrades")
        self.target: str = data.get("target", "")
        self.output_multiplier: float = data.get("output_multiplier", 1.0)
        self.synergy_source: str = data.get("synergy_source", "")
        self.synergy_per: float = data.get("synergy_per", 0.0)
        self.unlock_at: int = data.get("unlock_at", 0)

    def is_unlocked(self, inventory: dict) -> bool:
        """Generator upgrades unlock once you own enough of their target."""
        if self.unlock_at <= 0:
            return True
        return inventory.get(self.target, 0) >= self.unlock_at

    def cost_for(self, owned: int) -> int:
        """Current price given how many the user already owns."""
        if self.price_growth > 1.0:
            return round(self.cost * self.price_growth**owned)
        return self.cost

    def sell_value_for(self, owned: int) -> int:
        """Refund for selling one item while owning `owned` of them —
        SELL_RATE of the price that was paid for the most recent one."""
        return int(self.cost_for(max(owned - 1, 0)) * SELL_RATE)

    def fmt_name(self) -> str:
        return self.name.replace("_", " ").title()

    def fmt_shop_item(self, owned: int = 0) -> str:
        notes = []
        if self.cooldown_reduction > 0:
            mins = self.cooldown_reduction // 60
            notes.append(
                f"−{mins}min cooldown each" if self.ownership_limit != 1 else f"−{mins}min cooldown"
            )
        if self.beans_per_hour > 0:
            notes.append(f"+{self.beans_per_hour:,}/hr each")
        if self.bean_bonus > 0:
            notes.append(f"+{self.bean_bonus:.0%} beans each")
        if self.output_multiplier > 1.0:
            notes.append(f"×{self.output_multiplier:g} output")
        if self.unlock_at > 0:
            notes.append(f"needs {self.unlock_at}× {self.target.replace('_', ' ')}")
        if self.ownership_limit > 0:
            notes.append(f"owned {owned}/{self.ownership_limit}")
        elif owned > 0:
            notes.append(f"owned {owned}")
        subtext = " · ".join(notes)
        price = self.cost_for(owned)
        price_str = f"`{price:,}` beans"
        if self.price_growth > 1.0 and owned > 0:
            price_str = f"`{price:,}` beans (next)"
        return (
            f"{self.emoji} **{self.fmt_name()}** — {price_str}\n"
            f"-# {self.description}" + (f" · {subtext}" if subtext else "")
        )


SHOP_INVENTORY: list[Item] = [
    Item(data) for data in core.config.data["shop"]["items"]
]

ITEM_MAP: dict[str, Item] = {item.name: item for item in SHOP_INVENTORY}

SHOP_PAGES: list[tuple[str, list[Item]]] = [
    (title, items)
    for key, title in CATEGORY_ORDER
    if (items := [i for i in SHOP_INVENTORY if i.category == key])
]


async def item_autocomplete(
    interaction: Interaction, current: str
) -> list[app_commands.Choice[str]]:
    """Filtered item picker — the shop now has more than Discord's 25-choice cap."""
    cur = current.lower()
    matches = [
        i for i in SHOP_INVENTORY
        if cur in i.fmt_name().lower() or cur in i.name
    ]
    return [
        app_commands.Choice(name=f"{i.emoji} {i.fmt_name()}", value=i.name)
        for i in matches[:25]
    ]


async def sellable_autocomplete(
    interaction: Interaction, current: str
) -> list[app_commands.Choice[str]]:
    """Item picker for /sell — cosmetics are excluded since they can't be sold."""
    cur = current.lower()
    matches = [
        i for i in SHOP_INVENTORY
        if i.category != "cosmetics" and (cur in i.fmt_name().lower() or cur in i.name)
    ]
    return [
        app_commands.Choice(name=f"{i.emoji} {i.fmt_name()}", value=i.name)
        for i in matches[:25]
    ]


GENERATORS: list[Item] = [i for i in SHOP_INVENTORY if i.category == "generators"]
GENERATOR_UPGRADES: list[Item] = [
    i for i in SHOP_INVENTORY if i.category == "generator_upgrades"
]


class PermanentUpgrade:
    """A golden-bean upgrade that survives prestige."""

    def __init__(self, data: dict):
        self.name: str = data["name"]
        self.description: str = data["description"]
        self.emoji: str = data.get("emoji", "✨")
        self.base_cost: int = data["base_cost"]
        self.cost_growth: float = data.get("cost_growth", 1.0)
        self.max_level: int = data.get("max_level", 0)  # 0 = unlimited
        self.effect: str = data["effect"]
        self.effect_value: float = data.get("effect_value", 0.0)

    def fmt_name(self) -> str:
        return self.name.replace("_", " ").title()

    def cost_for(self, level: int) -> int:
        return round(self.base_cost * self.cost_growth**level)

    def at_max(self, level: int) -> bool:
        return self.max_level > 0 and level >= self.max_level


PERMANENT_UPGRADES: list[PermanentUpgrade] = [
    PermanentUpgrade(data) for data in core.config.data.get("permanent_upgrades", [])
]
PERMANENT_MAP: dict[str, PermanentUpgrade] = {u.name: u for u in PERMANENT_UPGRADES}

ACHIEVEMENTS: list[dict] = core.config.data.get("achievements", [])

# Mystery box loot tables, keyed by the box item's name. A "box" is any shop
# item that has a loot table here.
LOOT_TABLES: dict[str, list[dict]] = core.config.data.get("loot_tables", {})
BOX_NAMES: list[str] = list(LOOT_TABLES.keys())


def get_permanent_level(user_doc: dict, name: str) -> int:
    return user_doc.get("permanentUpgrades", {}).get(name, 0)


def _permanent_effect_total(user_doc: dict, effect: str) -> float:
    """Sum of effect_value × level across permanent upgrades of one effect type."""
    upgrades = user_doc.get("permanentUpgrades", {})
    return sum(
        u.effect_value * upgrades.get(u.name, 0)
        for u in PERMANENT_UPGRADES
        if u.effect == effect
    )


def get_achievement_bonus(user_doc: dict) -> float:
    """Total permanent multiplier fraction from unlocked achievements."""
    unlocked = set(user_doc.get("achievements", []))
    return sum(a.get("bonus", 0.0) for a in ACHIEVEMENTS if a["name"] in unlocked)


def get_cooldown_reduction(inventory: dict) -> int:
    """Returns total cooldown reduction in seconds from owned items."""
    return sum(
        inventory.get(item.name, 0) * item.cooldown_reduction
        for item in SHOP_INVENTORY
    )


def get_cooldown_floor(user_doc: dict) -> int:
    """Lowest the pet cooldown can go, lowered by Eternal Energy."""
    reduction = int(_permanent_effect_total(user_doc, "cooldown_floor"))
    return max(MIN_COOLDOWN - reduction, 300)  # never below 5 minutes


def get_effective_cooldown(user_doc: dict) -> int:
    """Pet cooldown after shop reductions, clamped to the (upgradable) floor."""
    base = core.config.data["cooldowns"]["pet"]
    inventory = user_doc.get("inventory", {})
    return max(base - get_cooldown_reduction(inventory), get_cooldown_floor(user_doc))


def get_collect_cap_hours(user_doc: dict) -> float:
    """Offline accrual cap; extended by Deep Pantry, removed by Auto-Collect."""
    if get_permanent_level(user_doc, "auto_collect") > 0:
        return float("inf")
    base = core.config.data["generators"]["collect_cap_hours"]
    return base + _permanent_effect_total(user_doc, "collect_cap")


def get_golden_pet_chance(user_doc: dict) -> float:
    """Base lucky-collar chance plus Lucky Whiskers."""
    return _permanent_effect_total(user_doc, "lucky")


def get_box_luck(user_doc: dict) -> float:
    """Extra mystery-box fortune from Lucky Whiskers."""
    return _permanent_effect_total(user_doc, "lucky")


def get_head_start_fraction(user_doc: dict) -> float:
    """Fraction of beans kept through prestige."""
    return min(_permanent_effect_total(user_doc, "head_start"), 0.95)


def get_bean_multiplier(user_doc: dict) -> float:
    """Global bean multiplier from Golden Paws, achievements and bonus items.
    Applies to pets, /collect, and /fish."""
    paws_bonus = _permanent_effect_total(user_doc, "multiplier")
    multiplier = 1.0 + paws_bonus
    multiplier *= 1.0 + get_achievement_bonus(user_doc)
    inventory = user_doc.get("inventory", {})
    for item in SHOP_INVENTORY:
        if item.bean_bonus > 0:
            multiplier *= 1.0 + item.bean_bonus * inventory.get(item.name, 0)
    return multiplier


def get_generator_rate(inventory: dict) -> int:
    """Total passive beans/hr from generators, after upgrades and synergies."""
    total = 0.0
    for gen in GENERATORS:
        owned = inventory.get(gen.name, 0)
        if owned == 0:
            continue
        factor = 1.0
        for up in GENERATOR_UPGRADES:
            if up.target != gen.name or inventory.get(up.name, 0) < 1:
                continue
            if up.output_multiplier > 1.0:
                factor *= up.output_multiplier
            if up.synergy_per > 0 and up.synergy_source:
                factor *= 1.0 + up.synergy_per * inventory.get(up.synergy_source, 0)
        total += owned * gen.beans_per_hour * factor
    return round(total)


def total_generators_owned(inventory: dict) -> int:
    return sum(inventory.get(g.name, 0) for g in GENERATORS)


def sync_generator_rate(user_id: int, inventory: dict) -> None:
    """Refresh the denormalized generatorRate field used by the leaderboard."""
    database.users.update_one(
        {"_id": str(user_id)},
        {"$set": {"generatorRate": get_generator_rate(inventory)}},
    )


def achievement_metrics(user_doc: dict) -> dict[str, int]:
    """Current value of every achievement metric for a user."""
    inventory = user_doc.get("inventory", {})
    return {
        "lifetime_beans": user_doc.get("totalBeansEarned", 0),
        "generators": total_generators_owned(inventory),
        "prestiges": user_doc.get("prestiges", 0),
        "highest_streak": user_doc.get("highestStreak", 0),
        "pets": user_doc.get("pets", 0),
    }


def check_achievements(user_id: int, user_doc: dict | None = None) -> list[dict]:
    """Unlock any newly-earned achievements, paying golden beans. Returns the
    list of achievements unlocked by this call (for surfacing to the user)."""
    user_doc = user_doc or find_user_or_default(user_id)
    unlocked = set(user_doc.get("achievements", []))
    metrics = achievement_metrics(user_doc)

    newly: list[dict] = []
    for ach in ACHIEVEMENTS:
        if ach["name"] in unlocked:
            continue
        if metrics.get(ach["metric"], 0) >= ach["threshold"]:
            # Guard with $nin so concurrent calls can't double-award
            doc = database.users.find_one_and_update(
                {"_id": str(user_id), "achievements": {"$nin": [ach["name"]]}},
                {
                    "$addToSet": {"achievements": ach["name"]},
                    "$inc": {"goldenBeans": ach.get("reward_golden", 0)},
                },
            )
            if doc is not None:
                newly.append(ach)
    return newly


def format_unlocks(newly: list[dict]) -> str:
    """A line to append to a response embed when achievements are unlocked."""
    if not newly:
        return ""
    golden_emoji = core.config.data["emojis"]["golden_beans"]
    lines = [
        f"🏆 **Achievement unlocked: {a['emoji']} {a['name'].replace('_', ' ').title()}**"
        + (f" `+{a['reward_golden']}` {golden_emoji}" if a.get("reward_golden") else "")
        for a in newly
    ]
    return "\n" + "\n".join(lines)


def attempt_purchase(user_id: int, item: Item) -> tuple[dict | None, int, str | None]:
    """Atomically buys one item at its current scaled price.
    Returns (updated_doc, price_paid, error_message)."""
    user_doc = find_user_or_default(user_id)
    inventory = user_doc.get("inventory", {})
    owned = inventory.get(item.name, 0)
    price = item.cost_for(owned)

    if not item.is_unlocked(inventory):
        return None, price, (
            f"**{item.fmt_name()}** is locked — own "
            f"{item.unlock_at}× {item.target.replace('_', ' ').title()} first."
        )

    query = {"_id": str(user_id), "beans": {"$gte": price}}
    if item.ownership_limit > 0:
        # $not matches both missing fields and counts below the limit
        query[f"inventory.{item.name}"] = {"$not": {"$gte": item.ownership_limit}}
    if item.price_growth > 1.0:
        # Price depends on the owned count, so require it to be unchanged
        query[f"inventory.{item.name}"] = (
            owned if owned > 0 else {"$not": {"$gte": 1}}
        )

    update = {"$inc": {f"inventory.{item.name}": 1, "beans": -price}}
    if item.beans_per_hour > 0 and user_doc.get("lastCollect") is None:
        # First generator starts the income clock now
        update["$set"] = {"lastCollect": datetime.now(timezone.utc)}

    doc = database.users.find_one_and_update(
        query, update, return_document=ReturnDocument.AFTER
    )
    if doc is not None:
        if item.category in ("generators", "generator_upgrades"):
            sync_generator_rate(user_id, doc.get("inventory", {}))
        return doc, price, None

    user_doc = find_user_or_default(user_id)
    owned = user_doc.get("inventory", {}).get(item.name, 0)
    if item.ownership_limit > 0 and owned >= item.ownership_limit:
        return None, price, (
            f"You already own the maximum of **{item.fmt_name()}** "
            f"({item.ownership_limit})."
        )
    beans_emoji = core.config.data["emojis"]["beans"]
    if user_doc.get("beans", 0) < item.cost_for(owned):
        return None, price, (
            f"Not enough beans. You need {beans_emoji} `{item.cost_for(owned):,}` "
            f"but only have `{user_doc.get('beans', 0):,}`."
        )
    return None, price, "The shop was busy — try that again."


def attempt_sell(user_id: int, item: Item) -> tuple[dict | None, int, str | None]:
    """Atomically sells one item for SELL_RATE of the price paid for it.
    Returns (updated_doc, refund, error_message)."""
    if item.category == "cosmetics":
        return None, 0, f"**{item.fmt_name()}** is a cosmetic and can't be sold."

    user_doc = find_user_or_default(user_id)
    owned = user_doc.get("inventory", {}).get(item.name, 0)
    if owned < 1:
        return None, 0, f"You don't own any **{item.fmt_name()}**."

    refund = item.sell_value_for(owned)
    doc = database.users.find_one_and_update(
        # Refund depends on the owned count, so require it to be unchanged
        {"_id": str(user_id), f"inventory.{item.name}": owned},
        {"$inc": {f"inventory.{item.name}": -1, "beans": refund}},
        return_document=ReturnDocument.AFTER,
    )
    if doc is None:
        return None, 0, "The shop was busy — try that again."
    if item.category in ("generators", "generator_upgrades"):
        sync_generator_rate(user_id, doc.get("inventory", {}))
    return doc, refund, None


def visible_page_items(page_items: list[Item], inventory: dict) -> list[Item]:
    """Hide generator upgrades that are still locked or already owned."""
    result = []
    for item in page_items:
        if item.category == "generator_upgrades":
            if not item.is_unlocked(inventory) or inventory.get(item.name, 0) >= 1:
                continue
        result.append(item)
    return result


def build_shop_embed(user_doc: dict, page: int, action: str | None = None) -> Embed:
    inventory = user_doc.get("inventory", {})
    beans = user_doc.get("beans", 0)
    beans_emoji = core.config.data["emojis"]["beans"]
    page_title, page_items = SHOP_PAGES[page]
    shown = visible_page_items(page_items, inventory)

    if shown:
        items = "\n".join(
            item.fmt_shop_item(owned=inventory.get(item.name, 0)) for item in shown
        )
    elif page_items and page_items[0].category == "generator_upgrades":
        items = "-# Buy more generators to unlock upgrades for them."
    else:
        items = "-# Nothing here right now."
    description = f"{beans_emoji} Your beans: `{beans:,}`\n\n{items}"
    if action:
        description += f"\n\n{action}"

    embed = Embed(
        color=core.config.data["colors"]["primary"],
        title=f"{core.config.data['bot']['name']} Shop — {page_title}",
        description=description,
    )
    embed.set_footer(
        text=f"Page {page + 1}/{len(SHOP_PAGES)} · Items sell back for {SELL_RATE:.0%} of what you paid"
    )
    return embed


class BuySelect(Select):
    def __init__(self, page_items: list[Item], inventory: dict):
        options = []
        for item in visible_page_items(page_items, inventory):
            owned = inventory.get(item.name, 0)
            at_limit = item.ownership_limit > 0 and owned >= item.ownership_limit
            options.append(
                SelectOption(
                    label=f"{item.fmt_name()} — {item.cost_for(owned):,} beans",
                    value=item.name,
                    emoji=item.emoji,
                    description="Owned limit reached" if at_limit else item.description[:100],
                )
            )
        if options:
            super().__init__(placeholder="Buy an item...", options=options[:25])
        else:
            super().__init__(
                placeholder="Nothing to buy here",
                options=[SelectOption(label="-", value="-")],
                disabled=True,
            )

    async def callback(self, interaction: Interaction):
        item = ITEM_MAP[self.values[0]]
        doc, price, error = attempt_purchase(interaction.user.id, item)
        if error:
            embed = Embed(color=core.config.data["colors"]["error"], description=error)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        action = f"✅ Bought {item.emoji} **{item.fmt_name()}** for `{price:,}` beans."
        await self.view.refresh(interaction, doc, action)


class SellSelect(Select):
    def __init__(self, inventory: dict):
        options = []
        for item in SHOP_INVENTORY:
            if item.category == "cosmetics":
                continue  # cosmetics can't be sold
            owned = inventory.get(item.name, 0)
            if owned > 0:
                options.append(
                    SelectOption(
                        label=f"{item.fmt_name()} — sell for {item.sell_value_for(owned):,} beans",
                        value=item.name,
                        emoji=item.emoji,
                        description=f"You own {owned}",
                    )
                )
        if options:
            super().__init__(placeholder="Sell an item...", options=options[:25])
        else:
            super().__init__(
                placeholder="Nothing to sell yet",
                options=[SelectOption(label="-", value="-")],
                disabled=True,
            )

    async def callback(self, interaction: Interaction):
        item = ITEM_MAP[self.values[0]]
        doc, refund, error = attempt_sell(interaction.user.id, item)
        if error:
            embed = Embed(color=core.config.data["colors"]["error"], description=error)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        action = f"💰 Sold {item.emoji} **{item.fmt_name()}** for `{refund:,}` beans."
        await self.view.refresh(interaction, doc, action)


def _pick_tier(tiers: list[dict], luck: float) -> dict:
    """Weighted choice across a loot table. Lucky Whiskers shifts weight from
    the luck_donor tier to the luck_target tier (net weight is preserved)."""
    weights = []
    for tier in tiers:
        w = tier.get("weight", 0.0)
        if tier.get("luck_target"):
            w += luck
        if tier.get("luck_donor"):
            w -= luck
        weights.append(max(w, 0.0))

    total = sum(weights) or 1.0
    r = random.random() * total
    cumulative = 0.0
    for tier, w in zip(tiers, weights):
        cumulative += w
        if r < cumulative:
            return tier
    return tiers[-1]


def _roll_box(user_id: int, box_name: str) -> tuple[str, int] | tuple[None, None]:
    """Atomically consume one box of `box_name` and roll a reward from its loot
    table. Returns (result_description, boxes_remaining) or (None, None) if the
    user owns no such box.
    """
    beans_emoji = core.config.data["emojis"]["beans"]
    golden_emoji = core.config.data["emojis"]["golden_beans"]
    tiers = LOOT_TABLES.get(box_name)
    if not tiers:
        return None, None

    doc = database.users.find_one_and_update(
        {"_id": str(user_id), f"inventory.{box_name}": {"$gte": 1}},
        {"$inc": {f"inventory.{box_name}": -1}},
        return_document=ReturnDocument.AFTER,
    )
    if doc is None:
        return None, None

    inventory = doc.get("inventory", {})
    multiplier = get_bean_multiplier(doc)
    tier = _pick_tier(tiers, get_box_luck(doc))
    label = tier.get("label", "")
    generator_changed = False

    def _give_beans(amount: int, multiplied: bool) -> str:
        if multiplied:
            amount = round(amount * multiplier)
        database.users.update_one(
            {"_id": str(user_id)},
            {"$inc": {"beans": amount, "totalBeansEarned": amount}},
        )
        note = f" `×{multiplier:.2f}`" if multiplied and multiplier > 1.01 else ""
        prefix = f"{label} " if label else ""
        return f"{prefix}{beans_emoji} `+{amount:,}` beans!{note}"

    if tier["type"] == "golden":
        amount = random.randint(tier["min"], tier["max"])
        database.users.update_one({"_id": str(user_id)}, {"$inc": {"goldenBeans": amount}})
        prefix = f"{label} " if label else ""
        result = f"{prefix}{golden_emoji} `+{amount}` golden beans!"
    elif tier["type"] == "item":
        pools = tier.get("pool", [])
        eligible = [
            i for i in SHOP_INVENTORY
            if i.category in pools
            and i.name not in BOX_NAMES
            and (i.ownership_limit == 0 or inventory.get(i.name, 0) < i.ownership_limit)
        ]
        if eligible:
            prize = random.choice(eligible)
            update = {"$inc": {f"inventory.{prize.name}": 1}}
            if prize.beans_per_hour > 0 and doc.get("lastCollect") is None:
                update["$set"] = {"lastCollect": datetime.now(timezone.utc)}
            database.users.update_one({"_id": str(user_id)}, update)
            generator_changed = prize.category in ("generators", "generator_upgrades")
            result = f"You found {prize.emoji} **{prize.fmt_name()}**!"
        else:
            result = _give_beans(
                random.randint(tier.get("fallback_min", 20000), tier.get("fallback_max", 50000)),
                multiplied=False,
            )
    else:  # "beans"
        result = _give_beans(
            random.randint(tier["min"], tier["max"]),
            multiplied=tier.get("multiplied", False),
        )

    # Refresh once for rate sync, achievements, and the remaining count
    fresh = database.users.find_one({"_id": str(user_id)}) or doc
    if generator_changed:
        sync_generator_rate(user_id, fresh.get("inventory", {}))
    result += format_unlocks(check_achievements(user_id, fresh))

    remaining = fresh.get("inventory", {}).get(box_name, 0)
    return result, remaining


class OpenBoxView(View):
    def __init__(self, user_id: int, box_name: str, remaining: int):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.box_name = box_name
        box = ITEM_MAP[box_name]
        self._btn = Button(
            label="Open Another",
            style=ButtonStyle.primary,
            emoji=box.emoji,
            disabled=(remaining == 0),
        )
        self._btn.callback = self._open_another
        self.add_item(self._btn)

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("These aren't your boxes!", ephemeral=True)
            return False
        return True

    async def _open_another(self, interaction: Interaction):
        box = ITEM_MAP[self.box_name]
        result, remaining = _roll_box(interaction.user.id, self.box_name)
        if result is None:
            self._btn.disabled = True
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(
                embed=Embed(
                    color=core.config.data["colors"]["error"],
                    description=f"You don't have any {box.emoji} **{box.fmt_name()}** left!",
                ),
                ephemeral=True,
            )
            return

        self._btn.disabled = (remaining == 0)
        embed = Embed(
            color=core.config.data["colors"]["secondary"],
            title=f"{box.emoji} {box.fmt_name()} opened!",
            description=f"{result}\n-# {box.fmt_name()}s left: {remaining}",
        )
        await interaction.response.edit_message(embed=embed, view=self)


class PageButton(Button):
    def __init__(self, label: str, delta: int, disabled: bool):
        super().__init__(label=label, style=ButtonStyle.primary, disabled=disabled, row=2)
        self.delta = delta

    async def callback(self, interaction: Interaction):
        user_doc = find_user_or_default(interaction.user.id)
        await self.view.refresh(interaction, user_doc, None, page_delta=self.delta)


class ShopView(View):
    def __init__(self, user_id: int, user_doc: dict, page: int = 0):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.page = page
        self.message = None
        inventory = user_doc.get("inventory", {})
        self.add_item(BuySelect(SHOP_PAGES[page][1], inventory))
        self.add_item(SellSelect(inventory))
        self.add_item(PageButton("◀ Previous", -1, disabled=page <= 0))
        self.add_item(PageButton("Next ▶", 1, disabled=page >= len(SHOP_PAGES) - 1))

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.user_id:
            embed = Embed(
                color=core.config.data["colors"]["error"],
                description="This isn't your shop! Open your own with `/shop`.",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    async def refresh(
        self,
        interaction: Interaction,
        user_doc: dict,
        action: str | None,
        page_delta: int = 0,
    ):
        """Rebuilds the embed and components after a transaction or page turn."""
        new_page = max(0, min(self.page + page_delta, len(SHOP_PAGES) - 1))
        new_view = ShopView(self.user_id, user_doc, new_page)
        new_view.message = self.message
        self.stop()
        await interaction.response.edit_message(
            embed=build_shop_embed(user_doc, new_page, action), view=new_view
        )

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


class Shop(Cog):
    """Shop cog"""

    def __init__(self, bot: Bot):
        self.bot = bot

    @app_commands.command(name="shop", description="Open the shop")
    async def shop(self, ctx: Interaction):
        user_doc = find_user_or_default(ctx.user.id)
        view = ShopView(ctx.user.id, user_doc)
        await ctx.response.send_message(embed=build_shop_embed(user_doc, 0), view=view)
        view.message = await ctx.original_response()

    @app_commands.command(name="buy", description="Buy an item from the shop")
    @app_commands.describe(item="The item to purchase")
    @app_commands.autocomplete(item=item_autocomplete)
    async def buy(self, ctx: Interaction, item: str):
        shop_item = ITEM_MAP.get(item)
        if shop_item is None:
            embed = Embed(
                color=core.config.data["colors"]["error"],
                description="That item doesn't exist. Pick one from the list or use `/shop`.",
            )
            return await ctx.response.send_message(embed=embed, ephemeral=True)
        doc, price, error = attempt_purchase(ctx.user.id, shop_item)
        if error:
            embed = Embed(color=core.config.data["colors"]["error"], description=error)
            return await ctx.response.send_message(embed=embed, ephemeral=True)

        beans_emoji = core.config.data["emojis"]["beans"]
        owned = doc.get("inventory", {}).get(shop_item.name, 0)
        owned_str = (
            f"**{owned}** / {shop_item.ownership_limit}"
            if shop_item.ownership_limit > 0
            else f"**{owned}**"
        )
        embed = Embed(
            color=core.config.data["colors"]["primary"],
            title=f"{shop_item.emoji} {shop_item.fmt_name()}",
            description=(
                f"Bought for {beans_emoji} `{price:,}` beans.\n"
                f"Owned: {owned_str} · `{doc.get('beans', 0):,}` remaining"
            ),
        )
        await ctx.response.send_message(embed=embed)

    @app_commands.command(name="sell", description="Sell an item back for 80% of what you paid")
    @app_commands.describe(item="The item to sell")
    @app_commands.autocomplete(item=sellable_autocomplete)
    async def sell(self, ctx: Interaction, item: str):
        shop_item = ITEM_MAP.get(item)
        if shop_item is None:
            embed = Embed(
                color=core.config.data["colors"]["error"],
                description="That item doesn't exist. Pick one from the list or use `/shop`.",
            )
            return await ctx.response.send_message(embed=embed, ephemeral=True)
        doc, refund, error = attempt_sell(ctx.user.id, shop_item)
        if error:
            embed = Embed(color=core.config.data["colors"]["error"], description=error)
            return await ctx.response.send_message(embed=embed, ephemeral=True)

        beans_emoji = core.config.data["emojis"]["beans"]
        owned = doc.get("inventory", {}).get(shop_item.name, 0)
        embed = Embed(
            color=core.config.data["colors"]["primary"],
            title=f"{shop_item.emoji} {shop_item.fmt_name()}",
            description=(
                f"Sold for {beans_emoji} `{refund:,}` beans.\n"
                f"Owned: **{owned}** · {beans_emoji} `{doc.get('beans', 0):,}` total"
            ),
        )
        await ctx.response.send_message(embed=embed)

    @app_commands.command(name="open", description="Open a mystery box or crate")
    @app_commands.describe(box="Which box to open")
    @app_commands.choices(
        box=[
            app_commands.Choice(name=f"{ITEM_MAP[n].emoji} {ITEM_MAP[n].fmt_name()}", value=n)
            for n in BOX_NAMES
        ]
    )
    async def open(self, ctx: Interaction, box: str = "mystery_box"):
        if box not in LOOT_TABLES:
            box = "mystery_box"
        box_item = ITEM_MAP[box]
        result, remaining = _roll_box(ctx.user.id, box)
        if result is None:
            embed = Embed(
                color=core.config.data["colors"]["error"],
                description=f"You don't have any {box_item.emoji} **{box_item.fmt_name()}s**. Grab one in `/shop`!",
            )
            return await ctx.response.send_message(embed=embed, ephemeral=True)

        embed = Embed(
            color=core.config.data["colors"]["secondary"],
            title=f"{box_item.emoji} {box_item.fmt_name()} opened!",
            description=f"{result}\n-# {box_item.fmt_name()}s left: {remaining}",
        )
        await ctx.response.send_message(embed=embed, view=OpenBoxView(ctx.user.id, box, remaining))

    @app_commands.command(name="inventory", description="View your items")
    async def inventory(self, ctx: Interaction):
        user_doc = find_user_or_default(ctx.user.id)
        inventory = user_doc.get("inventory", {})

        owned_items = [
            f"{item.emoji} **{item.fmt_name()}** ×{count}"
            for item in SHOP_INVENTORY
            if (count := inventory.get(item.name, 0)) > 0
        ]

        reduction = get_cooldown_reduction(inventory)
        effective = get_effective_cooldown(user_doc)

        embed = Embed(
            color=core.config.data["colors"]["primary"],
            title=f"{ctx.user.display_name}'s Inventory",
            description="\n".join(owned_items) if owned_items else "No items yet. Check out `/shop`!",
        )
        cooldown_value = f"**{effective / 3600:.1f}hrs**"
        if reduction > 0:
            cooldown_value += f" (−{reduction // 60}min from items)"
        embed.add_field(name="Pet Cooldown", value=cooldown_value, inline=False)

        rate = get_generator_rate(inventory)
        if rate > 0:
            embed.add_field(
                name="Generators",
                value=f"**{rate:,}** beans/hr — claim with `/collect`",
                inline=False,
            )

        multiplier = get_bean_multiplier(user_doc)
        if multiplier > 1.0:
            embed.add_field(
                name="Bean Multiplier",
                value=f"**×{multiplier:.2f}** (applies to pets, /collect, /fish)",
                inline=False,
            )

        await ctx.response.send_message(embed=embed)


async def setup(bot: Bot):
    await bot.add_cog(Shop(bot))
