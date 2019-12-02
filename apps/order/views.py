from django.shortcuts import render, redirect
from django.views.generic import View
from utils.mixin import LoginRequiredMixin
from django.urls import reverse
from apps.user.models import Address
from apps.goods.models import GoodsSKU
from apps.order.models import OrderInfo, OrderGoods
from django.http import JsonResponse, HttpResponse
from django_redis import get_redis_connection
from datetime import datetime
from django.db import transaction
import time
from django.conf import settings
from alipay import AliPay
# Create your views here.


class OrderPlaceView(LoginRequiredMixin, View):
    def post(self, request):
        user = request.user
        sku_ids = request.POST.getlist('sku_ids')
        if len(sku_ids) == 0:
            return redirect(reverse('goods:index'))
        addrs = Address.objects.filter(user=user)
        cart_key = 'cart_%d' % user.id
        conn = get_redis_connection('default')
        skus = []
        total_count = 0
        total_amount = 0
        for sku_id in sku_ids:
            sku = GoodsSKU.objects.get(id=sku_id)
            count = conn.hget(cart_key, sku_id)
            amount = sku.price * int(count)
            sku.count = int(count)
            sku.amount = amount
            skus.append(sku)
            total_count += int(count)
            total_amount += amount
        transit_price = 10
        total_pay = total_amount + transit_price

        context = {
            'addrs': addrs,
            'skus': skus,
            'total_count': total_count,
            'total_amount': total_amount,
            'transit_price': transit_price,
            'total_pay': total_pay,
            'sku_ids': ','.join(sku_ids)
        }

        return render(request, 'order/place_order.html', context)


class OrderCommitView(View):
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': 'Please Login'})
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.GET('sku_ids')

        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': 1, 'errmsg': 'Information is not completed'})

        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': 'Address does not exist'})

        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 3, 'errmsg': 'Payment method is not supported'})

        order_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(user.id)
        transit_price = 10
        total_count = 0
        total_price = 0

        order = OrderInfo.objects.create(order_id=order_id, user=user, addr=addr, pay_method=pay_method,
                                         total_count=total_count, total_price=total_price, transit_price=transit_price)

        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        sku_ids = sku_ids.split(',')

        for sku_id in sku_ids:
            try:
                sku = GoodsSKU.objects.get(id=sku_id)
            except GoodsSKU.DoesNotExist:
                return JsonResponse({'res': 4, 'errmsg': 'Product does not exist'})
            count = conn.hget(cart_key, sku_id)
            OrderGoods.objects.create(order=order, sku=sku, count=count, price=sku.price)

            sku.stock -= int(count)
            sku.sales += int(count)
            sku.save()
            total_count += int(count)
            total_price += sku.price * int(count)
        order.total_count = total_count
        order.total_price = total_price
        order.save()

        conn.hdel(cart_key, *sku_ids)
        return JsonResponse({'res': 5, 'errmsg': 'Submit Order Successfully!'})


class OrderCommitViewPessimisticLocking(View):
    @transaction.atomic
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': 'Please Login'})
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.GET('sku_ids')

        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': 1, 'errmsg': 'Information is not completed'})

        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': 'Address does not exist'})

        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 3, 'errmsg': 'Payment method is not supported'})

        order_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(user.id)
        transit_price = 10
        total_count = 0
        total_price = 0

        sid = transaction.savepoint()

        try:
            order = OrderInfo.objects.create(order_id=order_id, user=user, addr=addr, pay_method=pay_method,
                                             total_count=total_count, total_price=total_price, transit_price=transit_price)

            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            sku_ids = sku_ids.split(',')

            for sku_id in sku_ids:
                try:
                    sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
                except GoodsSKU.DoesNotExist:
                    transaction.savepoint_rollback(sid)
                    return JsonResponse({'res': 4, 'errmsg': 'Product does not exist'})
                count = conn.hget(cart_key, sku_id)
                if int(count) > sku.stock:
                    transaction.savepoint_rollback(sid)
                    return JsonResponse({'res': 6, 'errmsg': 'Product stock is not enough'})

                time.sleep(10)
                OrderGoods.objects.create(order=order, sku=sku, count=count, price=sku.price)

                sku.stock -= int(count)
                sku.sales += int(count)
                sku.save()
                total_count += int(count)
                total_price += sku.price * int(count)
            order.total_count = total_count
            order.total_price = total_price
            order.save()
        except Exception as e:
            transaction.savepoint_rollback(sid)
            return JsonResponse({'res': 7, 'errmsg': 'Placing order failed'})

        conn.hdel(cart_key, *sku_ids)
        return JsonResponse({'res': 5, 'errmsg': 'Submit Order Successfully!'})


class OrderCommitViewOptimisticLocking(View):
    @transaction.atomic
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': 'Please Login'})
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')

        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': 1, 'errmsg': 'Information is not completed'})

        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': 'Address does not exist'})

        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 3, 'errmsg': 'Payment method is not supported'})

        order_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(user.id)
        transit_price = 10
        total_count = 0
        total_price = 0

        sid = transaction.savepoint()

        try:
            order = OrderInfo.objects.create(order_id=order_id, user=user, addr=addr, pay_method=pay_method,
                                             total_count=total_count, total_price=total_price, transit_price=transit_price)

            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            sku_ids = sku_ids.split(',')

            for sku_id in sku_ids:
                for i in range(3):
                    try:
                        sku = GoodsSKU.objects.get(id=sku_id)
                    except GoodsSKU.DoesNotExist:
                        transaction.savepoint_rollback(sid)
                        return JsonResponse({'res': 4, 'errmsg': 'Product does not exist'})
                    count = conn.hget(cart_key, sku_id)
                    if int(count) > sku.stock:
                        transaction.savepoint_rollback(sid)
                        return JsonResponse({'res': 6, 'errmsg': 'Product stock is not enough'})

                    origin_stock = sku.stock
                    new_stock = origin_stock - int(count)
                    new_sales = sku.sales + int(count)
                    res = GoodsSKU.objects.filter(id=sku_id, stock=origin_stock).update(stock=new_stock, sales=new_sales)

                    if res == 0:
                        if i == 2:
                            transaction.savepoint_rollback(sid)
                            return JsonResponse({'res': 7, 'errmsg': 'Placing order failed'})
                        continue

                    OrderGoods.objects.create(order=order, sku=sku, count=count, price=sku.price)

                    total_count += int(count)
                    total_price += sku.price * int(count)
                    break

            order.total_count = total_count
            order.total_price = total_price
            order.save()
        except Exception as e:
            transaction.savepoint_rollback(sid)
            return JsonResponse({'res': 7, 'errmsg': 'Placing order failed'})

        conn.hdel(cart_key, *sku_ids)
        return JsonResponse({'res': 5, 'errmsg': 'Submit Order Successfully!'})


class OrderPayView(View):
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': 'Please Login'})
        order_id = request.POST.get('order_id')
        if not all([order_id]):
            return JsonResponse({'res': 1, 'errmsg': 'Information is not complete'})
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user, order_status=1, pay_method=3)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': 'Order does not exist'})

        ali_pay = AliPay(
                    appid=settings.ALIPAY_APP_ID,
                    app_notify_url=settings.ALIPAY_APP_NOTIFY_URL,
                    app_private_key_path=settings.APP_PRIVATE_KEY_PATH,
                    alipay_public_key_path=settings.APP_PRIVATE_KEY_PATH,
                    sign_type="RSA2",
                    debug=settings.ALIPAY_DEBUG
                    )
        total_pay = order.total_price + order.transit_price
        order_string = ali_pay.api_alipay_trade_page_pay(
                    out_trade_no=order_id,
                    total_amount=str(total_pay),
                    subject="UIR Seconded-Handed-ECommerce Platform %s" % order_id,
                    return_url='http://127.0.0.1:8000/order_check',
                    )
        pay_url = settings.ALIPAY_GATEWAY_URL + order_string
        return JsonResponse({'res': 3, 'pay_url': pay_url, 'errmsg': 'OK'})


class OrderCheckView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        order_id = request.GET.get('out_trade_no')
        if not all([order_id]):
            return JsonResponse({'res': 1, 'errmsg': 'information is not complete'})
        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          order_status=1,
                                          pay_method=3)
        except OrderInfo.DoesNotExist:
            return HttpResponse('Order does not exist')

        ali_pay = AliPay(appid=settings.ALIPAY_APP_ID,
                         app_notify_url=settings.ALIPAY_APP_NOTIFY_URL,
                         app_private_key_path=settings.APP_PRIVATE_KEY_PATH,
                         alipay_public_key_path=settings.ALIPAY_PUBLIC_KEY_PATH,
                         sign_type='RSA2',
                         debug=settings.ALIPAY_DEBUG
                         )
        response = ali_pay.api_alipay_trade_query(out_trade_no=order_id)
        res_code = response.get('code')
        if res_code == '10000' and response.get('trade_status') == 'TRADE_SUCCESS':
            order.order_status = 4
            order.trade_no = response.get('trade_no')
            order.save()
            return render(request, 'order/pay_result.html', {'pay_result': 'Payment succeed'})
        else:
            return render(request, 'order/pay_result.html', {'pay_result': 'Payment failed'})


class CommentView(LoginRequiredMixin, View):
    def get(self, request, order_id):
        user = request.user
        if not order_id:
            return redirect(reverse('user:order', kwargs={'page': 1}))
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:order', kwargs={"page": 1}))
        order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
        order_skus = OrderGoods.objects.filter(order_id=order_id)
        for order_sku in order_skus:
            amount = order_sku.count * order_sku.price
            order_sku.amount = amount
        order.order_skus = order_skus
        return render(request, 'order/order_comment.html', {'order': order})

    def post(self, request, order_id):
        user = request.user
        if not order_id:
            return redirect(reverse('user:order', kwargs={"page": 1}))
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("user:order", kwargs={"page": 1}))
        total_count = request.POST.get('total_count')
        total_count = int(total_count)

        for i in range(1, total_count+1):
            sku_id = request.POST.get('sku_%d' % i)
            content = request.POST.get('content_%d' % i, '')
            try:
                order_goods = OrderGoods.objects.get(order=order, sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue
            order_goods.comment = content
            order_goods.save()
        order.order_status = 5
        order.save()

        return redirect(reverse('user:order', kwargs={"page": 1}))

