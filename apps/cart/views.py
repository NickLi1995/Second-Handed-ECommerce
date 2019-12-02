from django.shortcuts import render
from django.views.generic import View
from django.http import JsonResponse
from django_redis import get_redis_connection
from apps.goods.models import GoodsSKU
from utils.mixin import LoginRequiredMixin
# Create your views here.


class CartAddView(View):
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': 'Please Login'})
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        if not all([sku_id, count]):
            return JsonResponse({'res': 2, 'errmsg': 'Info is not completed'})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': 'Product does not exist'})

        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 3, 'errmsg': 'Product amount must be a number'})

        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        cart_count = conn.hget(cart_key, sku_id)
        if cart_count:
            count += int(cart_count)
        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': 'Product stock is not enough'})

        conn.hset(cart_key, sku_id, count)
        cart_count = conn.hlen(cart_key)
        return JsonResponse({'res': 5, 'cart_count': cart_count, 'errmsg': 'Adding to cart successfully'})


class CartInfoView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = 'cart_%s' % request.user.id
            cart_count = conn.hlen(cart_key)
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        cart_dict = conn.hgetall(cart_key)
        total_count = 0
        total_amount = 0
        skus = []
        for sku_id, count in cart_dict.items():
            sku = GoodsSKU.objects.get(id=sku_id)
            amount = sku.price * int(count)
            sku.count = int(count)
            sku.amount = amount
            skus.append(sku)
            total_count += int(count)
            total_amount += amount
        context = {
            'total_count': total_count,
            'total_amount': total_amount,
            'skus': skus,
            'cart_count': cart_count
        }
        return render(request, 'cart/cart.html', context)


class CartUpdateView(View):
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': 'Please Login'})
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        if not all([sku_id, count]):
            return JsonResponse({"res": 1, 'errmsg': 'Info is not completed'})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': 'Product does not exist'})

        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 3, 'errmsg': 'Product amount must be a number'})

        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': 'Product stock is not enough'})

        conn.hset(cart_key, sku_id, count)
        cart_count = conn.hlen(cart_key)
        return JsonResponse({'res': 5, 'total_count': cart_count, 'errmsg': 'Updating cart successfully'})


class CartDeleteView(View):
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': 'Please Login'})

        sku_id = request.POST.get('sku_id')
        if not all([sku_id]):
            return JsonResponse({'res': 1, 'errmsg': 'Info is not completed'})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': 'Product does not exist'})

        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        conn.hdel(cart_key, 'sku_id')
        cart_count = conn.hlen(cart_key)
        return JsonResponse({'res': 3, 'total_count': cart_count, 'errmsg': 'Deleting cart successfully'})
