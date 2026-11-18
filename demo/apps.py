from django.apps import AppConfig


class DemoConfig(AppConfig):
    """Demo data only (the seed_demo command). No models."""

    name = "demo"
