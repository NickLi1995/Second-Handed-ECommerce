from django.db import models
from db.base_model import BaseModel
from tinymce.models import HTMLField
import os
import random
# Create your models here.


def get_filename_ext(filepath):
    base_name = os.path.basename(filepath)
    name, ext = os.path.splitext(base_name)
    return name, ext


def upload_image_path(instance, filename):
    new_filename = random.randint(1, 3910209312)
    name, ext = get_filename_ext(filename)
    final_filename = '{new_filename}{ext}'.format(new_filename=new_filename, ext=ext)
    return 'products/{new_filename}/{final_filename}'.format(new_filename=new_filename, final_filename=final_filename)


class GoodsType(BaseModel):
    name = models.CharField(max_length=20, verbose_name='type_name')
    logo = models.CharField(max_length=20, verbose_name='logo')
    image = models.ImageField(upload_to=upload_image_path, verbose_name='type_image')

    class Meta:
        db_table = 'df_goods_type'
        verbose_name = 'good_types'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Goods(BaseModel):
    name = models.CharField(max_length=20, verbose_name='goods_spu_name')
    detail = HTMLField(blank=True, verbose_name='goods_spu_detail')

    class Meta:
        db_table = 'df_goods'
        verbose_name = 'goods_spu'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class GoodsSKU(BaseModel):
    status_choices = (
        (0, 'not_on_sell'),
        (1, 'on_sell'),
    )

    category = models.ForeignKey(GoodsType, related_name='goods_sku', on_delete=models.CASCADE, verbose_name='good_type')
    goods = models.ForeignKey(Goods, related_name='good_sku', on_delete=models.CASCADE, verbose_name='good_spu')
    name = models.CharField(max_length=20, verbose_name='good_name')
    desc = models.CharField(max_length=256, verbose_name='good_description')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='good_price')
    unite = models.CharField(max_length=20, verbose_name='good_unit')
    image = models.ImageField(upload_to=upload_image_path, verbose_name='good_image')
    stock = models.IntegerField(default=1, verbose_name='good_stock')
    sales = models.IntegerField(default=0, verbose_name='good_sales')
    status = models.SmallIntegerField(default=1, choices=status_choices, verbose_name='good_status')

    class Meta:
        db_table = 'df_goods_sku'
        verbose_name = 'good'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class GoodsImage(BaseModel):
    sku = models.ForeignKey(GoodsSKU, on_delete=models.CASCADE, related_name='goods_image', verbose_name='good')
    image = models.ImageField(upload_to=upload_image_path, verbose_name='image_path')

    class Meta:
        db_table = 'df_goods_image'
        verbose_name = 'good_image'
        verbose_name_plural = verbose_name


class IndexTypeGoodsBanner(BaseModel):
    DISPLAY_TYPE_CHOICES = (
        (0, 'title'),
        (1, 'image')
    )

    DISPLAY_TYPE_DICT = {
        0: 'title',
        1: 'image'
    }

    category = models.ForeignKey(GoodsType, on_delete=models.CASCADE, related_name='index_type_goods', verbose_name='type')
    sku = models.ForeignKey(GoodsSKU, on_delete=models.CASCADE, related_name='index_type_goods', verbose_name='good')
    display_type = models.SmallIntegerField(default=1, choices=DISPLAY_TYPE_CHOICES, verbose_name='display_choice')
    index = models.SmallIntegerField(default=0, verbose_name='display_sequence')

    class Meta:
        db_table = 'df_index_type_goods'
        verbose_name = 'index_type_goods'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.category.name + '_' + self.sku.name + '_' + self.DISPLAY_TYPE_DICT[self.display_type]


class IndexGoodsBanner(BaseModel):
    sku = models.ForeignKey(GoodsSKU, on_delete=models.CASCADE, related_name='index_goods', verbose_name='good')
    image = models.ImageField(upload_to=upload_image_path, verbose_name='image')
    index = models.SmallIntegerField(default=0, verbose_name='display_sequence')

    class Meta:
        db_table = 'df_index_banner'
        verbose_name = 'index_goods'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.sku.name


class IndexPromotionBanner(BaseModel):
    name = models.CharField(max_length=20, verbose_name='promotion_name')
    url = models.CharField(max_length=256, verbose_name='promotion_url')
    image = models.ImageField(upload_to=upload_image_path, verbose_name='promotion_image')
    index = models.SmallIntegerField(default=0, verbose_name='display_sequence')

    class Meta:
        db_table = 'df_index_promotion'
        verbose_name = 'index_promotion'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

