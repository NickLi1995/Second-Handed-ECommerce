from django.conf import settings
from django.core.mail import send_mail
from django.template import loader
from apps.goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner
from celery_tasks.celery import app as app
import django
import os
import sys
sys.path.insert(0, './')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seconded_handed_ecommerce.settings')
# django.setup()


@app.task
def generate_static_index_html():
    types = GoodsType.objects.all()
    index_banner = IndexGoodsBanner.objects.all().order_by('index')
    promotion_banner = IndexPromotionBanner.objects.all().order_by('index')
    for category in types:
        image_banner = IndexTypeGoodsBanner.objects.filter(category=category, display_type=1)
        title_banner = IndexTypeGoodsBanner.objects.filter(category=category, display_type=0)
        category.title_banner = title_banner
        category.image_banner = image_banner
    cart_count = 0
    context = {
        'type': types,
        'index_banner': index_banner,
        'promotion_banner': promotion_banner,
        'cart_count': cart_count,
    }
    temp = loader.get_template('static_index.html')
    static_html = temp.render(context)
    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')
    with open(save_path, 'w') as f:
        f.write(static_html)


@app.task
def send_register_active_email(to_email, username, token):
    subject = 'Welcome to UIR Seconded-handed-ecommerce'
    message = ''
    sender = settings.DEFAULT_FROM_EMAIL
    receiver = [to_email]
    html_message = """
                    <h1>%s, Welcome to become a member of UIR Seconded-handed-ecommerce</h1>
                    Please click the following link to activate your account(expired in 7 hours)<br/>
                    <a href="http://%s/user/active/%s">http://%s/user/active/%s</a>
                   """ % (username, settings.BASE_URL, token, settings.BASE_URL, token)
    send_mail(subject, message, sender, receiver, html_message=html_message)
