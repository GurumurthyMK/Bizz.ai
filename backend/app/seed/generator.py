"""Deterministic demo-dataset generation (pure functions, seeded RNG only).

Everything derives from a single ``random.Random`` instance, so the same
``(seed, customers, anchor)`` triple always produces byte-identical output.
No database access here — the seeder inserts what this module returns.

Child rows reference parents by *position* (``customer_idx`` etc.); the
seeder resolves positions to database ids after inserting the parents.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from typing import Any


def _default_anchor() -> date:
    """Dataset "today" (UTC).

    An explicitly passed anchor keeps datasets byte-reproducible. The dynamic
    default exists because dashboards compute KPI windows from *now*: data
    ending months in the past leaves the current window empty and zeroes the
    Overview. Seed near the present, or pass a fixed anchor for reproducibility.
    """
    return datetime.now(UTC).date()


@dataclass(frozen=True)
class SeedConfig:
    seed: int = 42
    customers: int = 10000
    anchor: date = field(default_factory=_default_anchor)
    history_days: int = 365


@dataclass
class GeneratedDataset:
    products: list[dict[str, Any]] = field(default_factory=list)
    campaigns: list[dict[str, Any]] = field(default_factory=list)
    customers: list[dict[str, Any]] = field(default_factory=list)
    transactions: list[dict[str, Any]] = field(default_factory=list)
    interactions: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Catalog: (category, code, brand, name, base_price, popularity weight)
# ---------------------------------------------------------------------------

_CATALOG: tuple[tuple[str, str, str, str, float, int], ...] = (
    ("Electronics", "ELE", "Acme", "Wireless Headphones", 79.99, 5),
    ("Electronics", "ELE", "Acme", "True-Wireless Earbuds", 49.99, 5),
    ("Electronics", "ELE", "Volt", "Bluetooth Speaker", 59.99, 4),
    ("Electronics", "ELE", "Volt", "Smartwatch S2", 149.99, 3),
    ("Electronics", "ELE", "Volt", "USB-C Fast Charger", 19.99, 5),
    ("Electronics", "ELE", "Volt", "20000mAh Power Bank", 34.99, 4),
    ("Electronics", "ELE", "KeyPro", "Mechanical Keyboard", 69.99, 3),
    ("Electronics", "ELE", "KeyPro", "Wireless Mouse", 29.99, 4),
    ("Electronics", "ELE", "ViewMax", '27" Monitor', 229.99, 2),
    ("Electronics", "ELE", "ViewMax", '10" Tablet', 299.99, 2),
    ("Electronics", "ELE", "Lumen", "Mirrorless Camera", 399.99, 1),
    ("Electronics", "ELE", "Volt", "Drone X4", 499.99, 1),
    ("Electronics", "ELE", "KeyPro", "HD Webcam", 45.99, 3),
    ("Electronics", "ELE", "Volt", "1TB SSD", 89.99, 3),
    ("Electronics", "ELE", "Volt", "Noise-Cancelling Headphones Pro", 199.99, 2),
    ("Apparel", "APP", "ThreadLine", "Cotton T-Shirt", 19.99, 5),
    ("Apparel", "APP", "ThreadLine", "Slim Jeans", 49.99, 4),
    ("Apparel", "APP", "NorthPeak", "Winter Jacket", 89.99, 3),
    ("Apparel", "APP", "Stride", "Running Sneakers", 74.99, 4),
    ("Apparel", "APP", "ThreadLine", "Summer Dress", 59.99, 3),
    ("Apparel", "APP", "ThreadLine", "Hoodie", 44.99, 4),
    ("Apparel", "APP", "Stride", "Sports Socks 5pk", 9.99, 5),
    ("Apparel", "APP", "ThreadLine", "Cap", 14.99, 4),
    ("Apparel", "APP", "ThreadLine", "Formal Shirt", 34.99, 3),
    ("Apparel", "APP", "Stride", "Yoga Leggings", 29.99, 3),
    ("Apparel", "APP", "ThreadLine", "Denim Jacket", 69.99, 3),
    ("Home & Kitchen", "HOM", "HomeChef", "Cookware Set", 129.99, 3),
    ("Home & Kitchen", "HOM", "HomeChef", "Electric Kettle", 34.99, 4),
    ("Home & Kitchen", "HOM", "GlowWell", "Table Lamp", 29.99, 3),
    ("Home & Kitchen", "HOM", "SleepSoft", "Bedsheet Set", 45.99, 3),
    ("Home & Kitchen", "HOM", "CleanPro", "Vacuum V8", 159.99, 2),
    ("Home & Kitchen", "HOM", "HomeChef", "Air Fryer XL", 99.99, 4),
    ("Home & Kitchen", "HOM", "HomeChef", "Mug Set 4pc", 24.99, 3),
    ("Home & Kitchen", "HOM", "GlowWell", "LED Strip 5m", 16.99, 4),
    ("Home & Kitchen", "HOM", "SleepSoft", "Memory Pillow", 27.99, 3),
    ("Home & Kitchen", "HOM", "HomeChef", "Knife Set", 59.99, 2),
    ("Home & Kitchen", "HOM", "HomeChef", "Stand Mixer", 139.99, 2),
    ("Grocery", "GRO", "FarmFresh", "Arabica Coffee 500g", 12.99, 5),
    ("Grocery", "GRO", "FarmFresh", "Green Tea 100ct", 8.99, 4),
    ("Grocery", "GRO", "SnackBox", "Trail Mix", 5.99, 5),
    ("Grocery", "GRO", "FarmFresh", "Cold-Pressed Oil 1L", 9.99, 4),
    ("Grocery", "GRO", "NutriPlus", "Whey Protein 1kg", 29.99, 3),
    ("Grocery", "GRO", "FarmFresh", "Wild Honey 500g", 11.99, 3),
    ("Grocery", "GRO", "SnackBox", "Dark Chocolate 70%", 6.49, 4),
    ("Grocery", "GRO", "FarmFresh", "Basmati Rice 5kg", 14.99, 4),
    ("Grocery", "GRO", "NutriPlus", "Oats 1kg", 4.99, 4),
    ("Grocery", "GRO", "FarmFresh", "Almonds 500g", 13.99, 3),
    ("Grocery", "GRO", "NutriPlus", "Peanut Butter 1kg", 7.99, 4),
    ("Beauty", "BEA", "GlowLab", "Shampoo 400ml", 11.99, 4),
    ("Beauty", "BEA", "GlowLab", "Moisturizer", 18.99, 4),
    ("Beauty", "BEA", "GlowLab", "Vitamin C Serum", 24.99, 3),
    ("Beauty", "BEA", "GlowLab", "Matte Lipstick", 14.99, 3),
    ("Beauty", "BEA", "GlowLab", "Face Wash", 9.99, 4),
    ("Beauty", "BEA", "GlowLab", "Hair Oil", 12.99, 3),
    ("Beauty", "BEA", "GlowLab", "Sunscreen SPF50", 13.99, 4),
    ("Sports", "SPO", "FlexFit", "Yoga Mat", 29.99, 4),
    ("Sports", "SPO", "FlexFit", "Dumbbell Pair 10kg", 49.99, 3),
    ("Sports", "SPO", "FlexFit", "Steel Bottle 1L", 14.99, 4),
    ("Sports", "SPO", "NorthPeak", "Trek Backpack 45L", 39.99, 3),
    ("Sports", "SPO", "FlexFit", "Football", 19.99, 3),
    ("Sports", "SPO", "FlexFit", "Resistance Bands", 21.99, 3),
    ("Sports", "SPO", "Stride", "Badminton Set", 34.99, 2),
)

# (name, channel, type, status, start_offset_days, end_offset_days, budget)
_CAMPAIGNS: tuple[tuple[str, str, str, str, int, int, float], ...] = (
    ("Monsoon Sale 2026", "email", "seasonal", "completed", -120, -90, 80000),
    ("Festive Dhamaka", "ads", "seasonal", "completed", -60, -30, 150000),
    ("New Year Kickoff", "push", "promotional", "completed", -240, -210, 60000),
    ("Summer Essentials", "social", "seasonal", "completed", -180, -150, 70000),
    ("Winback Wave Q2", "email", "winback", "completed", -150, -120, 40000),
    ("Loyalty Rewards Boost", "sms", "retention", "completed", -100, -70, 35000),
    ("Clearance Carnival", "ads", "promotional", "completed", -45, -15, 90000),
    ("App Launch Push", "push", "awareness", "completed", -300, -270, 50000),
    ("Referral Rally", "social", "awareness", "active", -20, 10, 45000),
    ("Harvest Fest", "email", "seasonal", "active", -10, 20, 55000),
    ("Winter Preview", "sms", "seasonal", "draft", 30, 60, 30000),
    ("Dormant Revival", "email", "winback", "paused", -80, -50, 25000),
)

_FIRST_NAMES: tuple[str, ...] = (
    "Aarav",
    "Vihaan",
    "Arjun",
    "Sai",
    "Reyansh",
    "Krishna",
    "Ishaan",
    "Rohan",
    "Kabir",
    "Ananya",
    "Diya",
    "Aadhya",
    "Myra",
    "Sara",
    "Ira",
    "Priya",
    "Rahul",
    "Amit",
    "Neha",
    "Vikram",
    "Sneha",
    "Karan",
    "Pooja",
    "Manish",
    "Divya",
    "Sanjay",
    "Ritu",
    "Alok",
    "Farhan",
    "Zoya",
    "Imran",
    "Aditya",
    "Nisha",
    "Gaurav",
    "Tanvi",
    "Harsh",
    "Shreya",
    "Varun",
    "Meera",
    "Rajesh",
)

_LAST_NAMES: tuple[str, ...] = (
    "Sharma",
    "Verma",
    "Gupta",
    "Mehta",
    "Iyer",
    "Patel",
    "Reddy",
    "Nair",
    "Khan",
    "Singh",
    "Yadav",
    "Mishra",
    "Joshi",
    "Chandra",
    "Bose",
    "Das",
    "Kulkarni",
    "Menon",
    "Agarwal",
    "Jain",
    "Malhotra",
    "Kapoor",
    "Khanna",
    "Chopra",
    "Rao",
    "Naidu",
    "Pillai",
    "Shetty",
    "Bhatt",
    "Trivedi",
    "Desai",
    "Shah",
    "Fernandes",
    "Kumar",
    "Rani",
    "Devi",
    "Lal",
    "Prasad",
    "Pawar",
    "Anand",
)

# (city, weight)
_CITIES: tuple[tuple[str, int], ...] = (
    ("Mumbai", 20),
    ("Delhi", 16),
    ("Bengaluru", 14),
    ("Hyderabad", 10),
    ("Chennai", 8),
    ("Pune", 8),
    ("Kolkata", 7),
    ("Ahmedabad", 5),
    ("Jaipur", 4),
    ("Lucknow", 3),
    ("Surat", 2),
    ("Kochi", 2),
    ("Indore", 1),
)

# (country, weight)
_COUNTRIES: tuple[tuple[str, int], ...] = (
    ("India", 88),
    ("UAE", 4),
    ("USA", 3),
    ("UK", 2),
    ("Singapore", 2),
    ("Australia", 1),
)

# (domain, weight)
_DOMAINS: tuple[tuple[str, int], ...] = (
    ("gmail.com", 55),
    ("yahoo.com", 12),
    ("outlook.com", 10),
    ("hotmail.com", 6),
    ("icloud.com", 5),
    ("rediffmail.com", 5),
    ("protonmail.com", 2),
    ("fastmail.com", 2),
    ("zoho.com", 2),
    ("yandex.com", 1),
)

# (archetype, weight, orders_lambda, last_order_lo, last_order_hi, spend_mult, max_orders)
_ARCHETYPES: tuple[tuple[str, float, float, int, int, float, int | None], ...] = (
    ("champion", 0.05, 36.0, 0, 30, 2.0, None),
    ("loyal", 0.15, 18.0, 0, 45, 1.2, None),
    ("regular", 0.35, 11.0, 0, 90, 1.0, None),
    ("occasional", 0.20, 5.0, 0, 180, 0.8, None),
    ("at_risk", 0.12, 7.0, 90, 240, 0.9, None),
    ("new", 0.08, 2.5, 0, 30, 0.9, 3),
    ("dormant", 0.05, 3.0, 240, 365, 0.7, 4),
)

# Day-of-week purchase weights, Monday=0 (weekend bump).
_DOW_WEIGHTS: tuple[float, ...] = (0.90, 0.85, 0.90, 0.95, 1.10, 1.40, 1.30)

# (interaction_type, weight) for organic engagement.
_ORGANIC_TYPES: tuple[tuple[str, int], ...] = (
    ("visit", 30),
    ("open", 20),
    ("click", 20),
    ("call", 7),
    ("support", 8),
    ("review", 5),
    ("referral", 3),
)

# Plausible channels per interaction type.
_TYPE_CHANNELS: dict[str, tuple[str, ...]] = {
    "visit": ("web", "app", "store"),
    "open": ("email", "sms", "push"),
    "click": ("email", "sms", "social", "web", "app"),
    "call": ("phone",),
    "support": ("phone", "web", "app"),
    "review": ("web", "app"),
    "referral": ("social", "email", "app"),
    "purchase": ("web", "app", "store"),
}


def _weighted(rng: random.Random, choices: tuple[tuple[str, int], ...]) -> str:
    total = sum(weight for _, weight in choices)
    roll = rng.uniform(0, total)
    cumulative = 0.0
    for value, weight in choices:
        cumulative += weight
        if roll < cumulative:
            return value
    return choices[-1][0]


def _weighted_index(rng: random.Random, weights: list[float]) -> int:
    total = sum(weights)
    roll = rng.uniform(0, total)
    cumulative = 0.0
    for index, weight in enumerate(weights):
        cumulative += weight
        if roll < cumulative:
            return index
    return len(weights) - 1


def _poisson(rng: random.Random, lam: float) -> int:
    """Knuth's method; normal approximation for large lambda."""
    if lam >= 30:
        return max(0, round(rng.gauss(lam, math.sqrt(lam))))
    threshold = math.exp(-lam)
    count = 0
    product = 1.0
    while product > threshold:
        count += 1
        product *= rng.random()
    return count - 1


def _day_with_weekly_seasonality(rng: random.Random, earliest: date, latest: date) -> date:
    """Uniform day in range, rejection-sampled toward high-traffic weekdays."""
    span = (latest - earliest).days
    if span <= 0:
        return earliest
    peak = max(_DOW_WEIGHTS)
    while True:
        candidate = earliest + timedelta(days=rng.randrange(span + 1))
        if rng.random() * peak <= _DOW_WEIGHTS[candidate.weekday()]:
            return candidate


def _at(
    day: date, hour_lo: int = 8, hour_hi: int = 22, rng: random.Random | None = None
) -> datetime:
    moment = datetime.combine(day, time.min, tzinfo=UTC)
    if rng is not None:
        moment += timedelta(
            hours=rng.randrange(hour_lo, hour_hi),
            minutes=rng.randrange(60),
            seconds=rng.randrange(60),
        )
    return moment


def generate_products() -> list[dict[str, Any]]:
    """Hand-authored catalog — identical for every seed (assortment is fixed)."""
    products = []
    for index, (category, code, brand, name, price, popularity) in enumerate(_CATALOG):
        products.append(
            {
                "sku": f"{code}-{index + 1:03d}",
                "name": f"{brand} {name}",
                "category": category,
                "brand": brand,
                "unit_price": round(price, 2),
                "currency": "USD",
                "is_active": True,
                "_popularity": popularity,
            }
        )
    return products


def generate_campaigns(config: SeedConfig) -> list[dict[str, Any]]:
    campaigns = []
    for name, channel, kind, status, start_off, end_off, budget in _CAMPAIGNS:
        campaigns.append(
            {
                "name": name,
                "channel": channel,
                "campaign_type": kind,
                "status": status,
                "start_date": _at(config.anchor + timedelta(days=start_off)),
                "end_date": _at(config.anchor + timedelta(days=end_off)),
                "budget": round(budget, 2),
                "description": f"{name} ({kind}, via {channel}).",
            }
        )
    return campaigns


def _pick_archetype(rng: random.Random) -> tuple[str, float, int, int, float, int | None]:
    total = sum(weight for _, weight, *_ in _ARCHETYPES)
    roll = rng.uniform(0, total)
    cumulative = 0.0
    for name, weight, lam, lo, hi, mult, cap in _ARCHETYPES:
        cumulative += weight
        if roll < cumulative:
            return name, lam, lo, hi, mult, cap
    name, _, lam, lo, hi, mult, cap = _ARCHETYPES[-1]
    return name, lam, lo, hi, mult, cap


def generate_customers(
    rng: random.Random, config: SeedConfig
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Returns (customers, per-customer plans) for transaction generation."""
    customers: list[dict[str, Any]] = []
    plans: list[dict[str, Any]] = []
    for index in range(config.customers):
        first = rng.choice(_FIRST_NAMES)
        last = rng.choice(_LAST_NAMES)
        domain = _weighted(rng, _DOMAINS)
        email = f"{first.lower()}.{last.lower()}{index % 97}@{domain}"
        city = _weighted(rng, _CITIES)
        country = "India" if rng.random() < 0.94 else _weighted(rng, _COUNTRIES)
        phone = (
            f"+91-{rng.randrange(70000, 99999)}{rng.randrange(10000, 99999)}"
            if country == "India" and rng.random() < 0.8
            else None
        )
        archetype, lam, lo, hi, mult, cap = _pick_archetype(rng)
        customers.append(
            {
                "first_name": first,
                "last_name": last,
                "email": email,
                "phone": phone,
                "city": city,
                "country": country,
                "_archetype": archetype,
            }
        )
        plans.append(
            {
                "orders_lambda": lam,
                "last_lo": lo,
                "last_hi": hi,
                "spend_mult": mult,
                "max_orders": cap,
            }
        )
    return customers, plans


def generate_transactions(
    rng: random.Random,
    config: SeedConfig,
    plans: list[dict[str, Any]],
    products: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    earliest = config.anchor - timedelta(days=config.history_days)
    popularity = [product["_popularity"] for product in products]
    transactions: list[dict[str, Any]] = []
    for customer_idx, plan in enumerate(plans):
        count = _poisson(rng, plan["orders_lambda"])
        if plan["max_orders"] is not None:
            count = min(count, plan["max_orders"])
        count = max(count, 1)
        last_day = config.anchor - timedelta(
            days=rng.randrange(plan["last_lo"], plan["last_hi"] + 1)
        )
        # "new" customers only exist inside their recency window.
        window_start = max(earliest, last_day - timedelta(days=330))
        days = sorted(
            {_day_with_weekly_seasonality(rng, window_start, last_day) for _ in range(count)}
            | {last_day}
        )
        for day in days:
            product_idx = _weighted_index(rng, popularity)
            base_price = products[product_idx]["unit_price"]
            unit_price = round(base_price * rng.uniform(0.92, 1.08) * plan["spend_mult"], 2)
            roll = rng.random()
            if roll < 0.70:
                quantity = 1
            elif roll < 0.88:
                quantity = 2
            elif roll < 0.95:
                quantity = 3
            else:
                quantity = rng.randint(4, 5)
            gross = round(quantity * unit_price, 2)
            discount = (
                round(gross * rng.uniform(0.05, 0.20), 2)
                if rng.random() < 0.25 and gross > 0
                else 0.0
            )
            status_roll = rng.random()
            recent = (config.anchor - day).days <= 14
            if status_roll < 0.960 or (not recent and status_roll < 0.970):
                txn_status = "completed"
                refunded_at = None
            elif status_roll < 0.985:
                txn_status = "refunded"
                refunded_at = _at(day + timedelta(days=rng.randint(3, 10)), rng=rng)
            elif recent and status_roll < 0.995:
                txn_status = "pending"
                refunded_at = None
            else:
                txn_status = "cancelled"
                refunded_at = None
            transactions.append(
                {
                    "customer_idx": customer_idx,
                    "product_idx": product_idx,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "discount": discount,
                    "total_amount": round(gross - discount, 2),
                    "status": txn_status,
                    "transaction_date": _at(day, rng=rng),
                    "refunded_at": refunded_at,
                }
            )
    return transactions


def _campaigns_covering(campaigns: list[dict[str, Any]], day: date) -> list[int]:
    covering = []
    for index, campaign in enumerate(campaigns):
        if campaign["status"] not in ("completed", "active"):
            continue
        start = campaign["start_date"].date()
        end = campaign["end_date"].date()
        if start <= day <= end:
            covering.append(index)
    return covering


def generate_interactions(
    rng: random.Random,
    config: SeedConfig,
    plans: list[dict[str, Any]],
    transactions: list[dict[str, Any]],
    campaigns: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    earliest = config.anchor - timedelta(days=config.history_days)
    interactions: list[dict[str, Any]] = []

    for txn in transactions:
        if txn["status"] != "completed" or rng.random() >= 0.45:
            continue
        txn_day = txn["transaction_date"].date()
        # Attribute checkouts inside a live campaign window to that campaign
        # so conversion and revenue attribution stay observable.
        covering = _campaigns_covering(campaigns, txn_day)
        campaign_idx = rng.choice(covering) if covering and rng.random() < 0.5 else None
        interactions.append(
            {
                "customer_idx": txn["customer_idx"],
                "campaign_idx": campaign_idx,
                "interaction_type": "purchase",
                "channel": rng.choice(_TYPE_CHANNELS["purchase"]),
                "occurred_at": txn["transaction_date"] + timedelta(hours=rng.randint(0, 3)),
                "summary": None,
                "extra": {"source": "checkout"},
            }
        )

    for customer_idx in range(len(plans)):
        for _ in range(_poisson(rng, 3.5)):
            itype = _weighted(rng, _ORGANIC_TYPES)
            channel = rng.choice(_TYPE_CHANNELS[itype])
            day = _day_with_weekly_seasonality(rng, earliest, config.anchor)
            covering = _campaigns_covering(campaigns, day)
            campaign_idx = rng.choice(covering) if covering and rng.random() < 0.6 else None
            interactions.append(
                {
                    "customer_idx": customer_idx,
                    "campaign_idx": campaign_idx,
                    "interaction_type": itype,
                    "channel": channel,
                    "occurred_at": _at(day, rng=rng),
                    "summary": None,
                    "extra": None,
                }
            )
    return interactions


def generate(config: SeedConfig | None = None) -> GeneratedDataset:
    """Generate the full interconnected dataset for one seed triple."""
    config = config or SeedConfig()
    rng = random.Random(config.seed)
    products = generate_products()
    campaigns = generate_campaigns(config)
    customers, plans = generate_customers(rng, config)
    transactions = generate_transactions(rng, config, plans, products)
    interactions = generate_interactions(rng, config, plans, transactions, campaigns)
    return GeneratedDataset(
        products=products,
        campaigns=campaigns,
        customers=customers,
        transactions=transactions,
        interactions=interactions,
    )
