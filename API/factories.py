import random
from datetime import datetime, timedelta
from string import ascii_letters, digits

# Django
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from django.utils.text import slugify

# 3rd-party
import factory
from factory.django import DjangoModelFactory
from faker import Faker

from API.models import ProductCategory
from API.models import Product
from API.models import Order
from API.models import OrderProductListItem


fake = Faker(settings.LANGUAGE_CODE)

unique_words = {fake.word() for i in range(512)}


def cut_phrase(phrase):
    return (phrase[0:42] + '...') if len(phrase) > 45 else phrase


def pickrandom():
    pick = random.choice(tuple(unique_words))
    unique_words.remove(pick)
    return pick


def get_random_string(part_length: int = 4, parts: int = 1, parts_join: str = '-',
                      characters: str = ascii_letters + digits):
    return parts_join.join([f'{"".join(random.choices(characters, k=part_length))}' for _ in range(parts)])


def random_number(length=10):
    number = ''
    for i in range(0, length):
        number += f'{fake.random_digit()}'
    return number


class UserFactory(DjangoModelFactory):
    """User factory."""

    class Meta:
        model = get_user_model()

    username = factory.LazyAttribute(lambda a: f'{a.email.split("@")[0]}')
    first_name = factory.LazyAttribute(lambda a: f'{fake.first_name()}')
    last_name = factory.LazyAttribute(lambda a: f'{fake.last_name()}')
    email = factory.LazyFunction(lambda: f'{fake.email()}')
    password = factory.PostGenerationMethodCall('set_password', 'Test@1234')
    last_login = factory.LazyFunction(
        lambda: fake.date_time_between(
            datetime.now(),
            datetime.now() + timedelta(days=365),
            tzinfo=timezone.get_current_timezone()
        ),
    )

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        groups = [g for g in Group.objects.filter(name__in=settings.USERS_CUSTOM_GROUPS).values_list('id', flat=True)]
        self.groups.add(random.choice(groups))


class CategoryFactory(DjangoModelFactory):
    """:model:`API.ProductCategory` factory."""

    class Meta:
        model = ProductCategory

    name = factory.LazyFunction(lambda: fake.sentence(nb_words=2))


class ProductFactory(DjangoModelFactory):
    """:model:`API.Product` factory."""

    class Meta:
        model = Product

    name = factory.LazyFunction(lambda: fake.sentence(nb_words=2))
    description = factory.Faker('paragraph', locale='en')
    price = factory.LazyFunction(lambda: random.uniform(0.1, 1000.0))
    photo = factory.django.ImageField(width=512, height=512)
    seller = factory.Iterator(get_user_model().objects.all())
    category = factory.Iterator(ProductCategory.objects.all())


class OrderFactory(DjangoModelFactory):
    """:model:`API.Order` factory."""

    class Meta:
        model = Order

    client = factory.Iterator(Group.objects.get(name=settings.USER_CLIENT_GROUP_NAME).user_set.all())
    order_address = factory.LazyFunction(lambda: fake.address())

    @factory.post_generation
    def random_product_list(self, create, extracted, **kwargs):
        count = min(max(1, kwargs.get('count', 3)), 16)
        products = [ids for ids in Product.objects.all().values_list('id', flat=True)]
        products = random.sample(products, count)
        OrderProductListItem.objects.bulk_create([
            OrderProductListItem(
                order=self,
                product_id=products[i],
                quantity=random.randint(1, 32)
            ) for i in range(count)
        ], count)
        self.save()
