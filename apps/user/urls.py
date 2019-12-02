from django.urls import re_path
from apps.user.views import RegisterView, ActiveView, LoginView, LogoutView, AddressView, UserInfoView, UserOrderView

app_name = 'user'

urlpatterns = [
    re_path(r'^$', UserInfoView.as_view(), name='user'),
    re_path(r'^register/$', RegisterView.as_view(), name='register'),
    re_path(r'^active/(?P<token>.*)$', ActiveView.as_view(), name='active'),
    re_path(r'^login/$', LoginView.as_view(), name='login'),
    re_path(r'^logout/$', LogoutView.as_view(), name='logout'),
    re_path(r'^address/$', AddressView.as_view(), name='address'),
    re_path(r'^order/(?P<page>\d+)/$', UserOrderView.as_view(), name='order'),
]
