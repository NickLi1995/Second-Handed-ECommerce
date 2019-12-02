from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import HttpResponse
from django.views.generic import View
from apps.user.models import User, Address
from apps.goods.models import GoodsSKU
from apps.order.models import OrderInfo, OrderGoods
import re
from django.conf import settings
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from django.core.mail import send_mail
from celery_tasks import tasks
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from utils.mixin import LoginRequiredMixin, LoginRequiredView
from django_redis import get_redis_connection
from django.core.paginator import Paginator
# Create your views here.


class RegisterView(View):
    def get(self, request):
        return render(request, 'user/register.html')

    def post(self, request):
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')

        if not all([username, password, email]):
            return render(request, 'user/register.html', {'errmsg': 'Information is not completed'})

        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'user/register.html', {'errmsg': 'Email is not valid'})

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None

        if user is not None:
            return render(request, 'user/register.html', {'errmsg': 'The user has already registered'})

        user = User.objects.create_user(username, email, password)
        user.is_active = 0
        user.save()

        serializer = Serializer(settings.SECRET_KEY, 3600*7)
        info = {'confirm': user.id}
        token = serializer.dumps(info)
        token = token.decode()

        # subject = 'Welcome to UIR Seconded-handed-ecommerce'
        # message = ''
        # sender = settings.DEFAULT_FROM_EMAIL
        # receiver = [email]
        # html_message = """
        #                 <h1>%s, Welcome to become a member of UIR Seconded-handed-ecommerce</h1>
        #                 Please click the following link to activate your account(expired in 7 hours)<br/>
        #                 <a href="http://%s/user/active/%s">http://%s/user/active/%s</a>
        #                """ % (username, settings.BASE_URL, token, settings.BASE_URL, token)
        # send_mail(subject, message, sender, receiver, html_message=html_message)
        tasks.send_register_active_email.delay(email, username, token)
        return redirect(reverse('goods:index'))


class ActiveView(View):
    def get(self, request, token):
        serializer = Serializer(settings.SECRET_KEY, 3600 * 7)
        try:
            info = serializer.loads(token)
            user_id = info['confirm']
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()
            return redirect(reverse('user:login'))
        except SignatureExpired as e:
            return HttpResponse('Activation link has expired.')


class LoginView(View):
    def get(self, request):
        username = request.COOKIES.get('username')
        checked = 'checked'
        if username is None:
            username = ''
            checked = ''
        return render(request, 'user/login.html', {'username': username, 'checked': checked})

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('pwd')
        remember = request.POST.get('remember', None)
        if not all([username, password]):
            return render(request, 'user/login.html', {'errmsg': 'Information is not completed'})
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                next_url = request.GET.get('next', reverse('goods:index'))
                response = redirect(next_url)
                if remember == 'on':
                    response.set_cookie('username', username, max_age=7 * 24 * 3600)
                else:
                    response.delete_cookie('username')
                return response
            else:
                return render(request, 'user/login.html', {'errmsg': 'Account is not activated'})
        else:
            return render(request, 'user/login.html', {'errmsg': 'username or password is incorrect'})


class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect(reverse('user:login'))


class AddressView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = 'cart_%s' % request.user.id
            cart_count = conn.hlen(cart_key)
        default_address = Address.objects.get_default_address(user)
        all_address = Address.objects.get_all_address(user)
        context = {
            'address': default_address,
            'all_address': all_address,
            'page': 'address',
            'cart_count': cart_count
        }
        return render(request, 'user/user_center_site.html', context)

    def post(self, request):
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')
        set_default = request.POST.get('is_default')

        if not all([receiver, addr, phone, zip_code]):
            return render(request, 'user/user_center_site.html', {'errmsg': 'Information is not completed'})

        user = request.user
        address = Address.objects.get_default_address(user)

        is_default = True
        if address is not None:
            is_default = False

        Address.objects.create(user=user, receiver=receiver, addr=addr,
                               zip_code=zip_code, phone=phone, is_default=is_default)

        return redirect(reverse('user:address'))


class UserInfoView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = 'cart_%s' % request.user.id
            cart_count = conn.hlen(cart_key)
        address = Address.objects.get_default_address(user)

        conn = get_redis_connection('default')
        history_key = 'history_%d' % user.id
        sku_ids = conn.lrange(history_key, 0, 4)
        skus = []
        for sku_id in sku_ids:
            sku = GoodsSKU.objects.get(id=sku_id)
            skus.append(sku)
        context = {
            'address': address,
            'skus': skus,
            'page': 'user',
            'cart_count': cart_count
        }
        return render(request, 'user/user_center_info.html', context)


class UserOrderView(LoginRequiredMixin, View):
    def get(self, request, page):
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = 'cart_%s' % request.user.id
            cart_count = conn.hlen(cart_key)

        info_msg = 1
        try:
            order_infos = OrderInfo.objects.filter(user=user).order_by('-create_time')
        except OrderInfo.DoesNotExist:
            order_infos = None

        if order_infos is None:
            info_msg = 0
        context = {
            'page': 'order',
            'info_msg': info_msg,
        }

        if info_msg == 1:
            for order_info in order_infos:
                order_goods = OrderGoods.objects.filter(order=order_info)
                for order_good in order_goods:
                    amount = order_good.price * order_good.count
                    order_good.amount = amount
                order_info.order_goods = order_goods
                order_info.status_title = OrderInfo.ORDER_STATUS[order_info.order_status]
            paginator = Paginator(order_infos, 3)
            page = int(page)
            if page > paginator.num_pages:
                page = 1
            order_infos_page = paginator.page(page)
            num_pages = paginator.num_pages
            if num_pages < 5:
                pages = range(1, num_pages+1)
            elif page <= 3:
                pages = range(1, 6)
            elif num_pages - page <= 2:
                pages = range(num_pages-4, num_pages+1)
            else:
                pages = range(page-2, page+3)

            context = {
                'page': 'order',
                'order_infos': order_infos,
                'info_msg': pages,
                'pages': pages,
                'order_infos_page': order_infos_page,
                'cart_count': cart_count
            }

        return render(request, 'user/user_center_order.html', context)

