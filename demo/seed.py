"""Demo data for the localhost demo: accounts, products and product photos.

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
  left as it is: its stock is never overwritten and an inactive product is
  never reactivated. The one exception is the photo below.
* **Stock history:** a product created by this run starts at 0 and reaches its
  demo stock through recorded stock changes (deliveries, plus a few
  adjustments), made by the demo staff account through the stock helper.
  Products that already existed get no new history, so a rerun never
  duplicates history or changes stock.
* **Product photos:** a demo product with no image (or whose image file has
  gone missing from ``media/``) gets its placeholder photo from
  ``demo/images/``, with alt text describing it. An image that is already
  there, such as one staff uploaded, is never replaced. The photos are
  openly licensed; see ``demo/images/CREDITS.md``.
* Nothing else in the database is touched.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from django.contrib.auth.hashers import check_password
from django.core.files import File
from django.db import transaction

from accounts.models import User
from catalog.models import Category, Product
from stock.models import MovementKind
from stock.services import change_stock


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
class DemoStockChange:
    """One recorded stock change in a demo product's history, oldest first."""

    kind: MovementKind  # RECEIVE or ADJUST
    change: int
    reason: str = ""


def received(amount: int, note: str = "") -> DemoStockChange:
    return DemoStockChange(MovementKind.RECEIVE, amount, note)


def adjusted(change: int, reason: str) -> DemoStockChange:
    return DemoStockChange(MovementKind.ADJUST, change, reason)


@dataclass(frozen=True)
class DemoProduct:
    title: str
    category: str
    price: str
    stock: int
    description: str
    threshold: int = 5
    is_active: bool = True
    # How the stock got there, oldest first. It must add up to ``stock``.
    # Left empty, a product with stock gets one delivery of that amount.
    history: tuple[DemoStockChange, ...] = ()
    # Required for every demo product (keyword-only): a file in demo/images/
    # credited in CREDITS.md, and alt text describing that photo.
    image: str = field(kw_only=True)
    alt_text: str = field(kw_only=True)


# The account that records the demo stock history.
STAFF_EMAIL = next(a.email for a in DEMO_ACCOUNTS if a.role == "staff")

# Openly licensed placeholder photos, 800 x 600 JPEGs. Credits: images/CREDITS.md.
DEMO_IMAGE_DIR = Path(__file__).resolve().parent / "images"
HOODIE_PHOTO = {"image": "hoodie.jpg", "alt_text": "A person seen from behind in a red hoodie"}


# 15 active products (some low, some out of stock) and 1 inactive one.
DEMO_PRODUCTS: list[DemoProduct] = [
    # Textbooks
    DemoProduct(
        "Intro to Business Analytics (3rd ed.)",
        "Textbook",
        "89.99",
        12,
        "Required text for CIDM 3330. Covers spreadsheets, data cleaning and dashboards.",
        image="business-analytics.jpg",
        alt_text="A laptop showing bar and pie charts",
    ),
    DemoProduct(
        "Database Systems: Design and Use",
        "Textbook",
        "112.50",
        4,
        "Relational design, SQL and normalisation, with worked examples.",
        history=(
            received(6, "Fall semester order"),
            adjusted(-2, "2 copies water-damaged in storage"),
        ),
        image="database-systems.jpg",
        alt_text="Rows of server racks in a data centre",
    ),
    DemoProduct(
        "Principles of Microeconomics",
        "Textbook",
        "74.00",
        0,
        "Supply, demand and market structures for ECON 2302.",
        history=(
            received(10, "Publisher delivery"),
            adjusted(-10, "Wrong edition delivered, returned to the publisher"),
        ),
        image="microeconomics.jpg",
        alt_text="Three stacks of coins, each taller than the last",
    ),
    DemoProduct(
        "Technical Writing Handbook",
        "Textbook",
        "38.25",
        25,
        "A practical guide to reports, proposals and documentation.",
        image="technical-writing.jpg",
        alt_text="A silver pen resting on a blank writing pad",
    ),
    DemoProduct(
        "Calculus: Early Transcendentals",
        "Textbook",
        "129.99",
        6,
        "Limits, derivatives and integrals. Warns early: threshold 8.",
        threshold=8,
        image="calculus.jpg",
        alt_text="An open maths textbook and a pen on graph paper",
    ),
    # Merchandise (sizes are separate products)
    DemoProduct(
        "Buff Hoodie – Small",
        "Merchandise",
        "44.99",
        18,
        "Maroon fleece hoodie with the Buffs wordmark.",
        **HOODIE_PHOTO,
    ),
    DemoProduct(
        "Buff Hoodie – Medium",
        "Merchandise",
        "44.99",
        3,
        "Maroon fleece hoodie with the Buffs wordmark.",
        history=(received(4), adjusted(-1, "Display sample, taken off sale")),
        **HOODIE_PHOTO,
    ),
    DemoProduct(
        "Buff Hoodie – Large",
        "Merchandise",
        "44.99",
        0,
        "Maroon fleece hoodie with the Buffs wordmark.",
        **HOODIE_PHOTO,
    ),
    DemoProduct(
        "Buffs Logo T-Shirt – Medium",
        "Merchandise",
        "19.99",
        40,
        "Soft cotton tee in heather grey.",
        image="t-shirt.jpg",
        alt_text="Folded t-shirts in grey, navy, red, green and white",
    ),
    DemoProduct(
        "Maroon Water Bottle",
        "Merchandise",
        "14.50",
        22,
        "Insulated 20 oz stainless steel bottle.",
        image="water-bottle.jpg",
        alt_text="Four reusable water bottles in steel and blue",
    ),
    DemoProduct(
        "Buffs Lanyard",
        "Merchandise",
        "5.99",
        2,
        "Maroon lanyard with a safety breakaway. Slow seller: threshold 1.",
        history=(received(1), adjusted(+1, "Recount: found 1 in the back room")),
        threshold=1,
        image="lanyard.jpg",
        alt_text="A teal fabric lanyard laid out flat",
    ),
    # Lab kits
    DemoProduct(
        "Chemistry Lab Kit",
        "Lab Kit",
        "65.00",
        9,
        "Glassware, pipettes and safety gloves for CHEM 1411.",
        image="chemistry-kit.jpg",
        alt_text="Glass beakers and a conical flask holding clear liquid",
    ),
    DemoProduct(
        "Biology Dissection Kit",
        "Lab Kit",
        "72.00",
        5,
        "Stainless steel tools in a zip case for BIOL 1406.",
        image="dissection-kit.jpg",
        alt_text="Stainless steel forceps and scissors laid on a cloth",
    ),
    DemoProduct(
        "Physics Circuits Kit",
        "Lab Kit",
        "58.75",
        0,
        "Breadboard, resistors, LEDs and a multimeter for PHYS 2426.",
        image="circuits-kit.jpg",
        alt_text="A breadboard with chips, LEDs and jumper wires",
    ),
    DemoProduct(
        "Lab Safety Goggles",
        "Lab Kit",
        "12.99",
        30,
        "Anti-fog splash goggles that fit over glasses.",
        history=(
            received(24, "Opening delivery"),
            received(8, "Top-up order"),
            adjusted(-2, "2 pairs cracked in storage"),
        ),
        image="safety-goggles.jpg",
        alt_text="Clear safety glasses with blue arms",
    ),
    # Discontinued: never shown to customers.
    DemoProduct(
        "Buff Hoodie – XS (discontinued)",
        "Merchandise",
        "39.99",
        7,
        "No longer sold.",
        is_active=False,
        **HOODIE_PHOTO,
    ),
]


@dataclass
class SeedReport:
    """What a seed run did, for the command to print."""

    # (account, what happened, whether the documented password works for it)
    accounts: list[tuple[DemoAccount, str, bool]] = field(default_factory=list)
    products_created: int = 0
    products_existing: int = 0
    images_attached: int = 0
    stock_changes_recorded: int = 0


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


def _attach_demo_photo(product: Product, item: DemoProduct) -> bool:
    """Give ``product`` its demo photo if it has none, or its file has gone missing.

    An image that is already stored, such as one uploaded by staff, is never
    replaced. Returns whether a photo was attached. The stored copy gets a
    random name, like every product image.
    """
    if product.image and product.image.storage.exists(product.image.name):
        return False
    with open(DEMO_IMAGE_DIR / item.image, "rb") as photo:
        product.image = File(photo, name=item.image)
        product.alt_text = item.alt_text
        product.save(update_fields=["image", "alt_text"])
    return True


def stock_history_for(item: DemoProduct) -> tuple[DemoStockChange, ...]:
    """The stock changes that bring ``item`` from 0 to its demo stock, oldest first."""
    if item.history:
        return item.history
    if item.stock:
        return (received(item.stock, "Opening delivery"),)
    return ()


def _record_stock_history(product: Product, item: DemoProduct, staff: User) -> int:
    """Bring a newly created ``product`` to its demo stock through the stock helper.

    Returns how many stock changes were recorded.
    """
    history = stock_history_for(item)
    for step in history:
        change_stock(product, step.change, kind=step.kind, user=staff, reason=step.reason)
    return len(history)


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
        staff = User.objects.get(email=STAFF_EMAIL)

        for item in DEMO_PRODUCTS:
            category, _ = Category.objects.get_or_create(name=item.category)
            product, created = Product.objects.get_or_create(
                title=item.title,
                defaults={
                    "category": category,
                    "description": item.description,
                    "price": Decimal(item.price),
                    # Starts at 0; the stock history below brings it to item.stock.
                    "stock": 0,
                    "low_stock_threshold": item.threshold,
                    "is_active": item.is_active,
                },
            )
            if created:
                report.products_created += 1
                report.stock_changes_recorded += _record_stock_history(product, item, staff)
            else:
                report.products_existing += 1
            if _attach_demo_photo(product, item):
                report.images_attached += 1
    return report
