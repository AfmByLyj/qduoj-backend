# Generated by Django 2.1.7 on 2023-08-06 11:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0017_userprofile_ls_sc'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='scoreSpan',
            field=models.TextField(default=''),
        ),
    ]
