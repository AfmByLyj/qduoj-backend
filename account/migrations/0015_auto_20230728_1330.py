# Generated by Django 2.1.7 on 2023-07-28 13:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0014_userprofile_userspan'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='RL_score',
            field=models.IntegerField(default=1000),
        ),
    ]
