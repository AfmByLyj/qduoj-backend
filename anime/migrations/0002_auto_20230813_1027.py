# Generated by Django 2.1.7 on 2023-08-13 10:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anime', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='anime',
            name='coverImg',
            field=models.TextField(default='/public/anime/default.png'),
        ),
    ]
