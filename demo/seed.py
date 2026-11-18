"""Demo data for the localhost demo: accounts and products.

DEVELOPMENT-ONLY CREDENTIALS. The passwords below are public (they are in the
repository and printed by ``seed_demo``). They exist only so the class demo
can log straight in, and the command refuses to run unless the settings set
``ALLOW_DEMO_SEED = True`` (only ``config/settings/dev.py`` does).

Safe to run repeatedly. What a second run does:

* **Superuser:** created if missing. An existing account with that email is
  never changed, so its password is never overwritten.
* **Staff and customer demo accounts:** created if missing. If they exist,
  their names, role and password are reset to the values below, so the printed
  logins always work. A demo email that now belongs to a superuser is skipped.
* **Products:** created if missing (matched by title). An existing product is
  left exactly as it is: its stock is never overwritten and an inactive
  product is never reactivated.
* Nothing else in the database is touched.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from django.contrib.auth.hashers import check_password
from django.db import transaction

from accounts.models import User
from catalog.models import Category, Product


@dataclass(frozen=True)
class DemoAccount:
    email: str
    password: str
    first_name: str
    last_name: str
    role: str  # "superuser", "staff" or "customer"


DEMO_ACCOUNTS: list[DemoAccount] = [
    DemoAccount("owner@buffshop.test", "Owner-Demo-Pass-26", "Shop", "Owner", "superuser"),
    DemoAccount("staff@buffshop.test", "Staff-Demo-Pass-26", "Casey", "Morgan", "staff"),
    DemoAccount("alex@buffshop.test", "Customer-Demo-Pass-26", "Alex", "Rivera", "customer"),
    DemoAccount("sam@buffshop.test", "Customer-Demo-Pass-26", "Sam", "Chen", "customer"),
    DemoAccount("jordan@buffshop.test", "Customer-Demo-Pass-26", "Jordan", "Lee", "customer"),
]


@dataclass(frozen=True)
class DemoProduct:
    title: str
    category: str
    price: str
    stock: int
    description: str
    threshold: int = 5
    is_active: bool = True


# 15 active products (some low, some out of stock) and 1 inactive one.
DEMO_PRODUCTS: list[DemoProduct] = [
    # Textbooks
    DemoProduct(
        "Intro to Business Analytics (3rd ed.)",
        "Textbook",
        "89.99",
        12,
        "Required text for CIDM 3330. Covers spreadsheets, data cleaning and dashboards.",
    ),
    DemoProduct(
        "Database Systems: Design and Use",
        "Textbook",
        "112.50",
        4,
        "Relational design, SQL and normalisation, with worked examples.",
    ),
    DemoProduct(
        "Principles of Microeconomics",
        "Textbook",
        "74.00",
        0,
        "Supply, demand and market structures for ECON 2302.",
    ),
    DemoProduct(
        "Technical Writing Handbook",
        "Textbook",
        "38.25",
        25,
        "A practical guide to reports, proposals and documentation.",
    ),
    DemoProduct(
        "Calculus: Early Transcendentals",
        "Textbook",
        "129.99",
        6,
        "Limits, derivatives and integrals. Warns early: threshold 8.",
        threshold=8,
    ),
    # Merchandise (sizes are separate products)
    DemoProduct(
        "Buff Hoodie – Small",
        "Merchandise",
        "44.99",
        18,
        "Maroon fleece hoodie with the Buffs wordmark.",
    ),
    DemoProduct(
        "Buff Hoodie – Medium",
        "Merchandise",
        "44.99",
        3,
        "Maroon fleece hoodie with the Buffs wordmark.",
    ),
    DemoProduct(
        "Buff Hoodie – Large",
        "Merchandise",
        "44.99",
        0,
        "Maroon fleece hoodie with the Buffs wordmark.",
    ),
    DemoProduct(
        "Buffs Logo T-Shirt – Medium",
        "Merchandise",
        "19.99",
        40,
        "Soft cotton tee in heather grey.",
    ),
    DemoProduct(
        "Maroon Water Bottle", "Merchandise", "14.50", 22, "Insulated 20 oz stainless steel bottle."
    ),
    DemoProduct(
        "Buffs Lanyard",
        "Merchandise",
        "5.99",
        2,
        "Maroon lanyard with a safety breakaway. Slow seller: threshold 1.",
        threshold=1,
    ),
    # Lab kits
    DemoProduct(
        "Chemistry Lab Kit",
        "Lab Kit",
        "65.00",
        9,
        "Glassware, pipettes and safety gloves for CHEM 1411.",
    ),
    DemoProduct(
        "Biology Dissection Kit",
        "Lab Kit",
        "72.00",
        5,
        "Stainless steel tools in a zip case for BIOL 1406.",
    ),
    DemoProduct(
        "Physics Circuits Kit",
        "Lab Kit",
        "58.75",
        0,
        "Breadboard, resistors, LEDs and a multimeter for PHYS 2426.",
    ),
    DemoProduct(
        "Lab Safety Goggles",
        "Lab Kit",
        "12.99",
        30,
        "Anti-fog splash goggles that fit over glasses.",
    ),
    # Discontinued: never shown to customers.
    DemoProduct(
        "Buff Hoodie – XS (discontinued)",
        "Merchandise",
        "39.99",
        7,
        "No longer sold.",
        is_active=False,
    ),
]


@dataclass
class SeedReport:
    """What a seed run did, for the command to print."""

    # (account, what happened, whether the documented password works for it)
    accounts: list[tuple[DemoAccount, str, bool]] = field(default_factory=list)
    products_created: int = 0
    products_existing: int = 0


def _still_has_demo_password(user: User, account: DemoAccount) -> bool:
    """Whether ``user``'s stored password is still the documented one. Read-only."""
    return check_password(account.password, user.password)


def _seed_account(account: DemoAccount) -> tuple[str, bool]:
    """Create or refresh one demo account.

    Returns what happened, in words, and whether the documented password
    works for the account (so the command knows whether to print it).
    """
    user = User.objects.filter(email=account.email).first()

    if account.role == "superuser":
        if user is None:
            User.objects.create_superuser(
                account.email,
                account.password,
                first_name=account.first_name,
                last_name=account.last_name,
            )
            return "created", True
        # Never overwrite an existing superuser (or any account using this email).
        if _still_has_demo_password(user, account):
            return "already there, unchanged", True
        return "already there, unchanged (password was changed, not shown)", False

    if user is not None and user.is_superuser:
        return "belongs to a superuser, skipped (password not shown)", False

    status = "reset" if user is not None else "created"
    if user is None:
        user = User(email=account.email)
    user.first_name = account.first_name
    user.last_name = account.last_name
    user.is_staff = account.role == "staff"
    user.is_active = True
    user.set_password(account.password)
    user.save()
    return status, True


def seed_demo() -> SeedReport:
    """Create the demo accounts and products, following the rules in this module's docstring.

    Idempotent: a second run creates nothing new. Callers must check
    ``settings.ALLOW_DEMO_SEED`` first (the ``seed_demo`` command does).
    """
    report = SeedReport()
    with transaction.atomic():
        for account in DEMO_ACCOUNTS:
            status, password_works = _seed_account(account)
            report.accounts.append((account, status, password_works))

        for item in DEMO_PRODUCTS:
            category, _ = Category.objects.get_or_create(name=item.category)
            _, created = Product.objects.get_or_create(
                title=item.title,
                defaults={
                    "category": category,
                    "description": item.description,
                    "price": Decimal(item.price),
                    "stock": item.stock,
                    "low_stock_threshold": item.threshold,
                    "is_active": item.is_active,
                },
            )
            if created:
                report.products_created += 1
            else:
                report.products_existing += 1
    return report
