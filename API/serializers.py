from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.conf import settings

from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from django_countries.serializer_fields import CountryField

from API.models import ProductCategory
from API.models import Product
from API.models import Address
from API.models import Order
from API.models import OrderProductListItem
from API.models import DiscountCoupon


# region Models Serializers
class UserSerializer(ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('id', 'username', 'email')
        read_only_fields = fields


class UserCreateSerializer(ModelSerializer):
    account_type = serializers.ChoiceField(choices=(
        (settings.USER_CLIENT_GROUP_NAME, settings.USER_CLIENT_GROUP_NAME),
        (settings.USER_SELLER_GROUP_NAME, settings.USER_SELLER_GROUP_NAME),
    ), allow_blank=True, required=False)

    class Meta:
        model = get_user_model()
        fields = ['username', 'email', 'password', 'account_type']

    def create(self, validated_data):
        user_group_type = validated_data.pop('account_type', None)

        instance = self.Meta.model.objects.create_user(**validated_data)

        if instance.email is None or instance.email == '':
            instance.email = instance.username + "@email.com"

        user_group = Group.objects.get(name=user_group_type if user_group_type else settings.DEFAULT_USER_CUSTOM_GROUP)
        instance.groups.add(user_group)
        instance.save()

        return instance


class ProductCategorySerializer(ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ('id', 'name')
        read_only_fields = fields


class ProductSerializer(ModelSerializer):
    category = ProductCategorySerializer()
    seller = UserSerializer()

    class Meta:
        model = Product
        fields = ('id', 'name', 'description', 'price', 'category', 'photo', 'thumbnail', 'seller')
        read_only_fields = fields


class ProductManageSerializer(ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=ProductCategory.objects.all())
    seller = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.all())

    class Meta:
        model = Product
        fields = ('id', 'name', 'description', 'price', 'category', 'photo', 'thumbnail', 'seller')
        read_only_fields = ['id', 'thumbnail', 'seller']


class ProductTopLeastSellersSerializer(ModelSerializer):
    category = ProductCategorySerializer()
    sells_count = serializers.IntegerField()

    class Meta:
        model = Product
        fields = ('id', 'name', 'description', 'price', 'category', 'photo', 'thumbnail', 'sells_count')
        read_only_fields = fields


class ProductTopLeastProfitableSerializer(ModelSerializer):
    category = ProductCategorySerializer()
    sells_count = serializers.IntegerField()
    total_profit = serializers.DecimalField(max_digits=18, decimal_places=2)

    class Meta:
        model = Product
        fields = ('id', 'name', 'description', 'price', 'category', 'photo', 'thumbnail', 'sells_count', 'total_profit')
        read_only_fields = fields


class ProductListItemSerializer(ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())

    class Meta:
        model = OrderProductListItem
        fields = ('id', 'product', 'quantity')
        read_only_fields = fields


class ProductListItemCreateSerializer(ProductListItemSerializer):
    class Meta(ProductListItemSerializer.Meta):
        read_only_fields = ('id',)


class AddressSerializer(ModelSerializer):
    country = CountryField(country_dict=True, read_only=True)
    short_address = serializers.CharField(read_only=True)
    full_address = serializers.CharField(read_only=True)

    class Meta:
        model = Address
        fields = ('id', 'country', 'city', 'street', 'street_number', 'street_number_local', 'post_code', 'state',
                  'short_address', 'full_address')
        read_only_fields = fields


class OrderCreateAddressSerializer(AddressSerializer):
    class Meta(AddressSerializer.Meta):
        read_only_fields = ('id', 'short_address', 'full_address')


class OrderSerializer(ModelSerializer):
    client = UserSerializer()
    order_address = AddressSerializer()
    products_list = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ('id', 'client', 'order_address', 'order_date', 'payment_deadline', 'full_price', 'status', 'discount',
                  'final_price', 'products_list')
        read_only_fields = fields

    def get_products_list(self, obj):
        return ProductListItemSerializer(obj.products_list, many=True).data


class OrderCreateSerializer(ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.all())
    order_address = OrderCreateAddressSerializer()
    orderproductlistitem_set = ProductListItemCreateSerializer(many=True)

    class Meta:
        model = Order
        fields = ('client', 'order_address', 'orderproductlistitem_set', 'discount',)
        read_only_fields = ('id',)

    def create(self, validated_data):
        order_products = validated_data.pop('orderproductlistitem_set')
        address_data = validated_data.pop('order_address')
        discount = validated_data.pop('discount_id', None)

        if discount is not None:
            discount = DiscountCoupon.objects.get(pk=discount)
            discount.is_used = True
            discount.save()
            validated_data['discount'] = discount.discount
        else:
            validated_data['discount'] = 0.0

        order_address = Address.objects.create(**address_data)
        validated_data['order_address'] = order_address
        instance = super().create(validated_data)
        products_list = [
            OrderProductListItem(
                order=instance, product=item['product'], quantity=item['quantity']
            ) for item in order_products
        ]

        OrderProductListItem.objects.bulk_create(products_list)
        instance.save(update_full_price=True)

        return instance


class DiscountCouponSerializer(ModelSerializer):
    class Meta:
        model = DiscountCoupon
        fields = ('id', 'code', 'is_used', 'is_expired', 'valid_time', 'valid_date', 'discount')
        read_only_fields = ('id', 'is_expired', 'valid_date')
# endregion


# region Default serializers
class DiscountCouponCodesSerializer(serializers.Serializer):
    codes = serializers.ListField(child=serializers.CharField(), allow_empty=False, allow_null=False, min_length=1)
    flat = serializers.BooleanField(required=False)


class OrderStatusExtraExplanation(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.OrderStatus.choices)
    status_explanation = serializers.CharField(style={'base_template': 'textarea.html', 'rows': 10})
# endregion
