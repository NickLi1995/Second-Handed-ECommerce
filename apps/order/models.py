from django.db import models
from db.base_model import BaseModel
from apps.user.models import User, Address
from apps.goods.models import GoodsSKU
# Create your models here.


class OrderInfo(BaseModel):
    PAY_METHODS = {
        '1': 'Cash on Delivery',
        '2': 'WeChat Pay',
        '3': 'AliPay',
        '4': 'UniPay',
        '5': 'Credit Card'
    }

    PAY_METHOD_CHOICES = (
        (1, 'Cash on Delivery'),
        (2, 'WeChat Pay'),
        (3, 'AliPay'),
        (4, 'UniPay'),
        (5, 'Credit Card')
    )

    ORDER_STATUS = {
        1: 'unpaid',
        2: 'undelivered',
        3: 'delivered, waiting for pick up',
        4: 'unevaluated',
        5: 'completed'
    }

    ORDER_STATUS_CHOICES = (
        (1, 'unpaid'),
        (2, 'undelivered'),
        (3, 'delivered, waiting for pick up'),
        (4, 'unevaluated'),
        (5, 'completed'),
    )

    order_id = models.CharField(max_length=128, primary_key=True, verbose_name='order id')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders', verbose_name='user')
    addr = models.ForeignKey(Address, on_delete=models.CASCADE, related_name='orders', verbose_name='address')
    pay_method = models.SmallIntegerField(choices=PAY_METHOD_CHOICES, default=3, verbose_name='payment method')
    total_count = models.IntegerField(default=1, verbose_name='goods amount')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='goods total price')
    transit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='order shipment fee')
    order_status = models.SmallIntegerField(choices=ORDER_STATUS_CHOICES, default=1, verbose_name='order status')
    trade_no = models.CharField(max_length=128, default='', verbose_name='order number')

    class Meta:
        db_table = 'df_order_info'
        verbose_name = 'orders'
        verbose_name_plural = verbose_name


class OrderGoods(BaseModel):
    order = models.ForeignKey(OrderInfo, on_delete=models.CASCADE, related_name='goods', verbose_name='order')
    sku = models.ForeignKey(GoodsSKU, on_delete=models.CASCADE, related_name='order_goods', verbose_name='good_sku')
    count = models.IntegerField(default=1, verbose_name='goods amount')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='goods price')
    comment = models.CharField(max_length=256, default='', verbose_name='comments')

    class Meta:
        db_table = 'df_order_goods'
        verbose_name = 'order goods'
        verbose_name_plural = verbose_name
