from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from demo.seed import seed_demo


class Command(BaseCommand):
    help = (
        "Create demo accounts and products for the localhost demo. Safe to run twice. "
        "Refuses to run unless the settings allow it (development only)."
    )

    def handle(self, *args, **options):
        # Independent of DEBUG: only dev settings set ALLOW_DEMO_SEED = True.
        if not getattr(settings, "ALLOW_DEMO_SEED", False):
            raise CommandError(
                "seed_demo is for development only and these settings don't allow it "
                "(ALLOW_DEMO_SEED is not True). Nothing was changed."
            )

        report = seed_demo()

        self.stdout.write(
            f"Products: {report.products_created} created, "
            f"{report.products_existing} already there (left unchanged)."
        )
        self.stdout.write("")
        self.stdout.write("Demo logins (DEVELOPMENT ONLY, these passwords are public):")
        for account, status, password_works in report.accounts:
            shown = account.password if password_works else "(not shown)"
            self.stdout.write(f"  {account.role:<9}  {account.email:<22}  {shown:<22}  {status}")
        self.stdout.write(self.style.SUCCESS("Demo data is ready."))
