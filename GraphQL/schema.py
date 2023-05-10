from django.db.models import Q

import graphene
from graphene_django import DjangoObjectType

from API.models import ProductCategory
from API.models import Product
from API.models import Address
from API.models import Order
from API.models import OrderProductListItem


class ProductCategoryType(DjangoObjectType):
    class Meta:
        model = ProductCategory
        fields = ('id', 'name',)


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = ('id', 'name', 'description', 'price', 'category', 'photo', 'thumbnail', 'seller')


class ProductStatisticType(DjangoObjectType):
    class Meta:
        model = Product
        fields = ('id', 'name', 'description', 'price', 'category', 'photo', 'thumbnail', 'seller')

    sells_count = graphene.Int()


class AddressType(DjangoObjectType):
    class Meta:
        model = Address
        fields = ('id', 'country', 'city', 'street', 'street_number', 'street_number_local', 'post_code', 'state')

    short_address = graphene.String()
    full_address = graphene.String()


class OrderProductListItemType(DjangoObjectType):
    class Meta:
        model = OrderProductListItem
        fields = ('id', 'product', 'quantity')


class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = ('id', 'client', 'order_address', 'order_date', 'payment_deadline', 'full_price', 'is_paid')

    products_list = graphene.List(OrderProductListItemType)


def get_date_range_product_filter_from_kwargs(**kwargs):
    date_from_limit = kwargs.get("date_from", None)
    date_to_limit = kwargs.get("date_to", None)

    date_filter_query = Q()

    if date_from_limit:
        date_filter_query.add(Q(orderproductlistitem__order__order_date__gte=date_from_limit), Q.AND)
    if date_to_limit:
        date_filter_query.add(Q(orderproductlistitem__order__order_date__lte=date_to_limit), Q.AND)

    return date_filter_query


class APIQuery(graphene.ObjectType):
    all_categories = graphene.List(ProductCategoryType)
    category = graphene.Field(ProductCategoryType, id=graphene.ID(required=True))
    all_products = graphene.List(ProductType)
    product = graphene.Field(ProductType, id=graphene.ID(required=True))
    top_sellers = graphene.List(ProductStatisticType, date_from=graphene.String(required=False), date_to=graphene.String(required=False))
    least_sellers = graphene.List(ProductStatisticType, date_from=graphene.String(required=False), date_to=graphene.String(required=False))
    all_orders = graphene.List(OrderType)
    order = graphene.Field(OrderType, id=graphene.ID(required=True))

    def resolve_all_categories(self, info):
        return ProductCategory.objects.all()

    def resolve_category(self, info, id):
        try:
            return ProductCategory.objects.get(pk=id)
        except ProductCategory.DoesNotExist:
            return None

    def resolve_all_products(self, info):
        return Product.objects.select_related('category').all()

    def resolve_product(self, info, id):
        try:
            return Product.objects.select_related('category').get(pk=id)
        except Product.DoesNotExist:
            return None

    def resolve_top_sellers(self, info, **kwargs):
        return Product.objects.top_sellers(info.context.user, get_date_range_product_filter_from_kwargs(**kwargs))

    def resolve_least_sellers(self, info, **kwargs):
        return Product.objects.least_sellers(info.context.user, get_date_range_product_filter_from_kwargs(**kwargs))

    def resolve_all_orders(self, info):
        return Order.objects.all()

    def resolve_order(self, info, id):
        try:
            return Order.objects.get(pk=id)
        except Order.DoesNotExist:
            return None


schema = graphene.Schema(query=APIQuery)
