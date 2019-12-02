from django.urls import re_path
from apps.order.views import OrderPlaceView, OrderCommitView, OrderCommitViewOptimisticLocking, OrderPayView, \
    OrderCheckView, CommentView

app_name = 'order'

urlpatterns = [
    re_path(r'^place/$', OrderPlaceView.as_view(), name='place'),
    re_path(r'^commit/$', OrderCommitViewOptimisticLocking.as_view(), name='commit'),
    re_path(r'^pay/$', OrderPayView.as_view(), name='pay'),
    re_path(r'^check/$', OrderCheckView.as_view(), name='check'),
    re_path(r'^comment/(?P<order_id>.*)/$', CommentView.as_view(), name='comment')
]
