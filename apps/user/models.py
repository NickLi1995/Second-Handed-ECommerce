from django.contrib.auth.models import AbstractUser
from db.base_model import BaseModel
from django.db import models
# Create your models here.


class User(AbstractUser, BaseModel):

    class Meta:
        db_table = 'df_user'
        verbose_name = 'site_user'
        verbose_name_plural = verbose_name


class AddressManager(models.Manager):
    def get_default_address(self, user):
        try:
            address = self.get(user=user, is_default=True)
        except self.model.DoesNotExist:
            address = None
        return address

    def get_all_address(self, user):
        try:
            all_address = self.filter(user=user)
        except self.model.DoesNotExist:
            all_address = None
        return all_address


class Address(BaseModel):
    user = models.ForeignKey(User, related_name='address', on_delete=models.CASCADE, verbose_name='user')
    receiver = models.CharField(max_length=20, verbose_name='receiver')
    addr = models.CharField(max_length=256, verbose_name='address')
    zip_code = models.CharField(max_length=5, null=True, verbose_name='zip_code')
    phone = models.CharField(max_length=10, verbose_name='phone_number')
    is_default = models.BooleanField(default=False, verbose_name='is_default_address')

    objects = AddressManager()

    class Meta:
        db_table = 'df_address'
        verbose_name = 'address'
        verbose_name_plural = verbose_name
