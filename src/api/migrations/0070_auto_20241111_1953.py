# Generated by Django 3.2.20 on 2024-11-11 19:53

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0069_merge_0068_auto_20241028_2238_0068_auto_20241031_2238"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="gfcrrevenue",
            name="annual_revenue",
        ),
        migrations.AddField(
            model_name="gfcrrevenue",
            name="revenue_amount",
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=11, verbose_name="Revenue amount in USD"
            ),
        ),
        migrations.AlterField(
            model_name="gfcrindicatorset",
            name="f1_1",
            field=models.DecimalField(
                decimal_places=3,
                default=0,
                max_digits=9,
                verbose_name="Total area of coral reefs in GFCR Programme (sq.km)",
            ),
        ),
        migrations.AlterField(
            model_name="gfcrindicatorset",
            name="f3_2",
            field=models.PositiveSmallIntegerField(
                default=0, verbose_name="Number of in situ coral reef restoration projects"
            ),
        ),
        migrations.AlterField(
            model_name="gfcrindicatorset",
            name="f3_3",
            field=models.PositiveSmallIntegerField(
                default=0,
                verbose_name="Number of coral reef restoration plans, technologies, strategies or guidelines developed",
            ),
        ),
        migrations.AlterField(
            model_name="gfcrindicatorset",
            name="f3_4",
            field=models.PositiveSmallIntegerField(
                default=0, verbose_name="Number of coral reef restoration trainings"
            ),
        ),
        migrations.AlterField(
            model_name="gfcrindicatorset",
            name="f3_5a",
            field=models.PositiveSmallIntegerField(
                default=0, verbose_name="Number of people engaged in coral reef restoration [men]"
            ),
        ),
        migrations.AlterField(
            model_name="gfcrindicatorset",
            name="f3_5b",
            field=models.PositiveSmallIntegerField(
                default=0, verbose_name="Number of people engaged in coral reef restoration [women]"
            ),
        ),
        migrations.AlterField(
            model_name="gfcrindicatorset",
            name="f3_5c",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                verbose_name="Number of people engaged in coral reef restoration [youth]",
            ),
        ),
        migrations.AlterField(
            model_name="gfcrindicatorset",
            name="f3_5d",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                verbose_name="Number of people engaged in coral reef restoration [indigenous]",
            ),
        ),
        migrations.AlterField(
            model_name="gfcrindicatorset",
            name="f3_6",
            field=models.PositiveSmallIntegerField(
                default=0,
                verbose_name="Number of response plans to support coral reef restoration after severe shocks",
            ),
        ),
        migrations.AlterField(
            model_name="gfcrindicatorset",
            name="f4_2",
            field=models.DecimalField(
                decimal_places=1,
                default=0,
                max_digits=4,
                verbose_name="Average macroalgae cover (%)",
            ),
        ),
        migrations.AlterField(
            model_name="gfcrindicatorset",
            name="f5_4a",
            field=models.PositiveSmallIntegerField(
                default=0,
                verbose_name="Number of local practitioners trained / supported in coral reef conservation and management [men]",
            ),
        ),
        migrations.AlterField(
            model_name="gfcrindicatorset",
            name="f5_4b",
            field=models.PositiveSmallIntegerField(
                default=0,
                verbose_name="Number of local practitioners trained / supported in coral reef conservation and management [women]",
            ),
        ),
        migrations.AlterField(
            model_name="gfcrindicatorset",
            name="f5_4c",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                verbose_name="Number of local practitioners trained / supported in coral reef conservation and management [youth]",
            ),
        ),
        migrations.AlterField(
            model_name="gfcrindicatorset",
            name="f5_4d",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                verbose_name="Number of local practitioners trained / supported in coral reef conservation and management [indigenous]",
            ),
        ),
        migrations.AlterField(
            model_name="gfcrindicatorset",
            name="f7_4",
            field=models.PositiveSmallIntegerField(
                default=0,
                verbose_name="Number of governance reforms/policies to support response and recovery to external shocks",
            ),
        ),
    ]
