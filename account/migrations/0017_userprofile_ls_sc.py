# Generated by Django 2.1.7 on 2023-07-29 08:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0016_userprofile_rl_get'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='ls_sc',
            field=models.IntegerField(default=1000),
        ),
    ]