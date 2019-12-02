from django.db import models


class BaseModel(models.Model):
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='created time')
    update_time = models.DateTimeField(auto_now_add=True, verbose_name='updated time')
    is_delete = models.BooleanField(default=False, verbose_name='deleted marker')

    class Meta:
        abstract = True
