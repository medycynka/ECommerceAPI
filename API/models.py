from django.core.files.base import ContentFile
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone
from django.utils.text import gettext_lazy as _
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.functions import Coalesce
from django.db.models.functions import Cast

from PIL import Image
import os
from io import BytesIO
from datetime import timedelta

# Create your models here.


class ProductCategory(models.Model):
    name = models.CharField(verbose_name=_("Category name"), max_length=128)

    class Meta:
        db_table = 'API_product_category'
        verbose_name = 'product category'
        verbose_name_plural = 'product categories'

    def __str__(self):
        return self.name


class ProductManager(models.Manager):
    def products_by_seller(self, seller: User, filter_q: Q = None):
        q = self.get_queryset()

        if filter_q:
            q = q.filter(Q(seller=seller) & filter_q if seller.is_superuser else filter_q)
        else:
            q = q.all() if seller.is_superuser else q.filter(seller=seller)

        return q

    def top_sellers(self, seller: User, filter_q: Q = None):
        """
        Get products in order from most to least frequently purchased
        :param seller: user model representing 'seller'
        :param filter_q: optional filter for filtering products list before ordering based on purchased counts (ex. get
        list of products form date range)
        :return: products in order from most to least frequently purchased
        """
        q = self.products_by_seller(seller, filter_q).select_related('category').prefetch_related('orderproductlistitem_set__order')

        return q.annotate(
            sells_count=Coalesce(models.Sum('orderproductlistitem__quantity'), Cast(0, models.PositiveIntegerField()))
        ).order_by('-sells_count')

    def least_sellers(self, seller: User, filter_q: Q = None):
        """
        Get products in order from least to most frequently purchased
        :param seller: user model representing 'seller'
        :param filter_q: optional filter for filtering products list before ordering based on purchased counts (ex. get
        list of products form date range)
        :return: products in order from least to most frequently purchased
        """
        q = self.products_by_seller(seller, filter_q).select_related('category').prefetch_related('orderproductlistitem_set__order')

        return q.annotate(
            sells_count=Coalesce(models.Sum('orderproductlistitem__quantity'), Cast(0, models.PositiveIntegerField()))
        ).order_by('sells_count')


class Product(models.Model):
    name = models.CharField(verbose_name=_("Product name"), max_length=128)
    description = models.TextField(verbose_name=_("Product description"), blank=True, default='')
    price = models.DecimalField(verbose_name=_("Product price"), decimal_places=2, max_digits=6)   # up to 9999.99
    category = models.ForeignKey('API.ProductCategory', verbose_name=_("Product category"), null=True,
                                 on_delete=models.SET_NULL)
    photo = models.ImageField(verbose_name=_("Product photo"), upload_to='photos')
    thumbnail = models.ImageField(verbose_name=_("Product thumbnail"), upload_to='thumbnails', blank=True, default=None)
    seller = models.ForeignKey(User, verbose_name=_("Product seller"), null=True, on_delete=models.CASCADE)

    objects = ProductManager()

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'API_product'
        verbose_name = 'product'
        verbose_name_plural = 'products'

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.create_thumbnail()

        super().save(force_insert=force_insert, force_update=force_update, using=using,
                                  update_fields=update_fields)

    def create_thumbnail(self):
        """
        Create a thumbnail image from provided `photo` file
        """

        thumbnail = Image.open(self.photo)
        thumbnail.thumbnail(settings.THUMBNAIL_SIZE, Image.ANTIALIAS)

        thumbnail_name, thumbnail_extension = os.path.splitext(self.photo.name)
        thumbnail_extension = thumbnail_extension.lower()
        thumb_filename = thumbnail_name + '_thumbnail' + thumbnail_extension

        if thumbnail_extension in ['.jpg', '.jpeg']:
            file_type = 'JPEG'
        elif thumbnail_extension == '.png':
            file_type = 'PNG'
        else:
            raise ValueError("Wrong product photo image! Accepted extensions are: jpg, jpeg or png!")

        temp_thumbnail = BytesIO()
        thumbnail.save(temp_thumbnail, file_type)
        temp_thumbnail.seek(0)

        self.thumbnail.save(thumb_filename, ContentFile(temp_thumbnail.read()), save=False)
        temp_thumbnail.close()


class Address(models.Model):
    class Countries(models.TextChoices):
        """
        Represents available shipping countries
        """
        PL = 'pl', _('Polska')
        EN = 'en', _('England')

    class PolishStates(models.IntegerChoices):
        """
        Polish voivodeship
        """
        NONE = 0, _('None')
        DS = 1, _('Dolnośląskie')
        KP = 2, _('Kujawsko-pomorskie')
        LB = 3, _('Lubelskie')
        LS = 4, _('Lubuskie')
        LD = 5, _('Łódzkie')
        MP = 6, _('Małopolskie')
        MZ = 7, _('Mazowieckie')
        OP = 8, _('Opolskie')
        PK = 9, _('Podkarpackie')
        PL = 10, _('Podlaskie')
        PM = 11, _('Pomorskie')
        SL = 12, _('Śląskie')
        SK = 13, _('Świętokrzyskie')
        WM = 14, _('Warmińsko-mazurskie')
        WP = 15, _('Wielkopolskie')
        ZP = 16, _('Zachodnio-pomorskie')

    country = models.CharField(_("Country"), choices=Countries.choices, blank=True, default=Countries.PL, max_length=8)
    city = models.CharField(_("City"), max_length=128)
    street = models.CharField(_("Street"), max_length=128)
    street_number = models.CharField(_("Street number"), max_length=16)
    street_number_local = models.CharField(_("Street number local"), max_length=16, blank=True, default="")
    post_code = models.CharField(_("Postal code"), max_length=8)
    state = models.PositiveSmallIntegerField(_("Polish voivodeship"), choices=PolishStates.choices, blank=True,
                                             default=PolishStates.NONE)

    class Meta:
        db_table = "API_address"
        verbose_name = 'address'
        verbose_name_plural = 'addresses'

    def __str__(self):
        street_number_local = "/" + self.street_number_local if self.street_number_local else ""
        voivodeship = " woj. " + self.get_state_display() if self.state != Address.PolishStates.NONE else ""
        return f'{self.street} {self.street_number}{street_number_local}, {self.post_code} {self.city}, ' \
               f'{self.get_country_display()}{voivodeship}'

    @property
    def short_address(self):
        street_number_local = "/" + self.street_number_local if self.street_number_local else ""
        return f'{self.street} {self.street_number}{street_number_local}, {self.post_code} {self.city}'

    @property
    def full_address(self):
        return self.__str__()

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.country != Address.Countries.PL and self.state != Address.PolishStates.NONE:
            self.state = Address.PolishStates.NONE
        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)


class Order(models.Model):
    client = models.ForeignKey(User, verbose_name=_("Client"), null=True, on_delete=models.SET_NULL)
    order_address = models.ForeignKey('API.Address', verbose_name=_("Order address"), null=True, on_delete=models.SET_NULL)
    order_date = models.DateTimeField(verbose_name=_("Order date"), blank=True)
    payment_deadline = models.DateTimeField(verbose_name=_('Payment deadline'), blank=True)
    full_price = models.DecimalField(verbose_name=_('Order summary price'), blank=True, null=True, decimal_places=2,
                                     max_digits=20)
    is_paid = models.BooleanField(verbose_name=_('Id order paid?'), blank=True, default=False)

    class Meta:
        db_table = "API_order"

    @property
    def products_list(self):
        """
        :return: :model:`Common.Product` list associated with this order
        """
        return OrderProductListItem.objects.select_related('product', 'product__category').filter(
            order=self
        ).only('product', 'quantity')

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if not self.order_date:
            self.order_date = timezone.now()
        if not self.payment_deadline:
            self.payment_deadline = self.order_date + timedelta(days=settings.PAYMENT_DEADLINE_DAYS)
        if not self.full_price and self.products_list.exists():
            self.full_price = self.products_list.aggregate(
                full_price=models.Sum(F('product__price') * F('quantity'), output_field=models.DecimalField())
            )['full_price']

        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)


class OrderProductListItem(models.Model):
    """
    Representation of the relationship between the product and the order taking into account the
    quantity of the related product
    """
    order = models.ForeignKey('API.Order', verbose_name=_("Order"), on_delete=models.CASCADE)
    product = models.ForeignKey('API.Product', verbose_name=_("Product"), on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(verbose_name=_("Quantity"), blank=True, default=1,
                                           validators=[MinValueValidator(1)])

    class Meta:
        db_table = "API_order_product_list_item"
