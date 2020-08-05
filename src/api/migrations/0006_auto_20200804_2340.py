# Generated by Django 2.2.12 on 2020-08-04 23:40
import django.core.validators
from django.db import migrations, models
from ..models.view_models import model_view_migrations
class Migration(migrations.Migration):
    dependencies = [
        ('api', '0005_auto_20200717_1917'),
    ]
    operations = [
        migrations.RunSQL(model_view_migrations.reverse_sql(), model_view_migrations.forward_sql()),
        migrations.AlterField(
            model_name='benthictransect',
            name='len_surveyed',
            field=models.DecimalField(decimal_places=1, max_digits=3, validators=[django.core.validators.MinValueValidator(10), django.core.validators.MaxValueValidator(100)], verbose_name='transect length surveyed (m)'),
        ),
        migrations.AlterField(
            model_name='fishbelttransect',
            name='len_surveyed',
            field=models.DecimalField(decimal_places=1, max_digits=3, validators=[django.core.validators.MinValueValidator(10), django.core.validators.MaxValueValidator(100)], verbose_name='transect length surveyed (m)'),
        ),
        migrations.RunSQL(model_view_migrations.forward_sql(), model_view_migrations.reverse_sql()),
    ]