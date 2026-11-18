import factory

from accounts.models import User

DEFAULT_PASSWORD = "Buffalo-Stampede-26"


class UserFactory(factory.django.DjangoModelFactory):
    """A customer account. Use ``StaffFactory`` / ``SuperuserFactory`` for other roles."""

    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"customer{n}@buffs.wtamu.edu")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    password = factory.PostGenerationMethodCall("set_password", DEFAULT_PASSWORD)

    @factory.post_generation
    def save_password(obj, create, extracted, **kwargs):  # noqa: N805
        if create:
            obj.save()


class StaffFactory(UserFactory):
    is_staff = True


class SuperuserFactory(UserFactory):
    is_staff = True
    is_superuser = True
