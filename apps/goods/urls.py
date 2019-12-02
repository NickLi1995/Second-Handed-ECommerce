from django.urls import re_path
from apps.goods.views import IndexView, DetailView, ListView

app_name = 'goods'

urlpatterns = [
    re_path(r'^$', IndexView.as_view(), name='index'),
    re_path(r'^list/(?P<type_id>\d+)/(?P<page>\d+)$', ListView.as_view(), name='list'),
    re_path(r'^goods/(?P<sku_id>\d+)$', DetailView.as_view(), name='detail'),
]
