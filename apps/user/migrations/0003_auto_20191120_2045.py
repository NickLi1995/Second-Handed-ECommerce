# Generated by Django 2.2.7 on 2019-11-21 02:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0002_address'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='user',
            options={'verbose_name': 'site_user', 'verbose_name_plural': 'site_user'},
        ),
        migrations.RenameField(
            model_name='address',
            old_name='is_defualt',
            new_name='is_default',
        ),
    ]