"""Seed the three starting categories. After this, they are edited in /admin/."""

from django.db import migrations

CATEGORIES = ["Textbook", "Merchandise", "Lab Kit"]


def add_categories(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    for name in CATEGORIES:
        Category.objects.get_or_create(name=name)


def remove_unused_categories(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Category.objects.filter(name__in=CATEGORIES, products__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_categories, remove_unused_categories),
    ]
