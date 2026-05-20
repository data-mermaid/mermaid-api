from django.db import migrations, models

GOI_DENSITY_BOUNDS = {
    "conchs": 3000,
    "corallivorous snails": 600,
    "crabs / shrimps": 1250,
    "crown-of-thorns starfish (COTS)": 125,
    "giant clams": 600,
    "lobsters": 300,
    "octopus": 125,
    "other invertebrates": 3000,
    "pearl oysters": 3000,
    "polychaete worms": 12500,
    "sea cucumbers": 3000,
    "sea urchins": 5500,
    "triton's trumpets": 30,
    "trochus shells": 3000,
    "turban shells": 3000,
}


def seed_density_upper_bound(apps, schema_editor):
    InvertGroupOfInterest = apps.get_model("api", "InvertGroupOfInterest")
    for goi in InvertGroupOfInterest.objects.all():
        goi.density_upper_bound = GOI_DENSITY_BOUNDS.get(goi.name, 3000)
        goi.save(update_fields=["density_upper_bound"])


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0115_goi_schema_finalize"),
    ]

    operations = [
        migrations.AddField(
            model_name="invertgroupofinterest",
            name="density_upper_bound",
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.RunPython(seed_density_upper_bound, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="invertgroupofinterest",
            name="density_upper_bound",
            field=models.PositiveIntegerField(),
        ),
    ]
