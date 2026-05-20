from django.db import migrations

SUPERUSER_APPROVED = 90


def populate_genus_group_of_interest(apps, schema_editor):
    """Walk genus → family → order → class_goi → group_of_interest and populate the new FK."""
    InvertGenus = apps.get_model("api", "InvertGenus")
    genera = list(InvertGenus.objects.select_related("family__order__class_goi__group_of_interest"))
    for genus in genera:
        genus.group_of_interest_id = genus.family.order.class_goi.group_of_interest_id
    InvertGenus.objects.bulk_update(genera, ["group_of_interest_id"])


def populate_order_invert_class(apps, schema_editor):
    """Walk order → class_goi → invert_class and populate the new FK."""
    InvertOrder = apps.get_model("api", "InvertOrder")
    orders = list(InvertOrder.objects.select_related("class_goi__invert_class"))
    for order in orders:
        order.invert_class_id = order.class_goi.invert_class_id
    InvertOrder.objects.bulk_update(orders, ["invert_class_id"])


def promote_goi_to_invert_attribute(apps, schema_editor):
    """Create an InvertAttribute row for each InvertGroupOfInterest using the same UUID.

    By reusing the same UUID, any FK in InvertGenus.group_of_interest_id that was
    populated in the previous step continues to resolve correctly after the PK swap
    in migration 0115 — no FK value updates are needed.
    """
    InvertAttribute = apps.get_model("api", "InvertAttribute")
    InvertGroupOfInterest = apps.get_model("api", "InvertGroupOfInterest")

    gois = list(InvertGroupOfInterest.objects.all())
    for goi in gois:
        InvertAttribute.objects.create(id=goi.id, status=SUPERUSER_APPROVED)
        goi.invertattribute_ptr_id = goi.id
    InvertGroupOfInterest.objects.bulk_update(gois, ["invertattribute_ptr_id"])


def deduplicate_invert_order(apps, schema_editor):
    """Merge duplicate InvertOrder rows (same name, different class_goi) into one.

    The canonical row is the one whose class_goi.group_of_interest.name sorts
    alphabetically first, for determinism.  All InvertFamily rows pointing to
    non-canonical orders are re-pointed to the canonical row before deletion.
    """
    InvertAttribute = apps.get_model("api", "InvertAttribute")
    InvertOrder = apps.get_model("api", "InvertOrder")
    InvertFamily = apps.get_model("api", "InvertFamily")

    orders = list(
        InvertOrder.objects.select_related("class_goi__group_of_interest").order_by("name")
    )
    by_name = {}
    for order in orders:
        by_name.setdefault(order.name, []).append(order)

    for name, dups in by_name.items():
        if len(dups) <= 1:
            continue
        canonical = min(dups, key=lambda o: o.class_goi.group_of_interest.name)
        non_canonical_ids = [o.pk for o in dups if o.pk != canonical.pk]
        InvertFamily.objects.filter(order_id__in=non_canonical_ids).update(order=canonical)
        InvertAttribute.objects.filter(pk__in=non_canonical_ids).delete()


def deduplicate_invert_family(apps, schema_editor):
    """Merge duplicate InvertFamily rows (same name + order) created by order merge.

    After order de-duplication both Muricidae rows share the same (name, order) pair.
    The canonical row is chosen by lowest pk (alphabetical UUID sort).  All InvertGenus
    rows pointing to non-canonical families are re-pointed before deletion.
    """
    InvertAttribute = apps.get_model("api", "InvertAttribute")
    InvertFamily = apps.get_model("api", "InvertFamily")
    InvertGenus = apps.get_model("api", "InvertGenus")

    families = list(InvertFamily.objects.order_by("name", "order_id"))
    by_key = {}
    for family in families:
        key = (family.name, str(family.order_id))
        by_key.setdefault(key, []).append(family)

    for key, dups in by_key.items():
        if len(dups) <= 1:
            continue
        canonical = min(dups, key=lambda f: str(f.pk))
        non_canonical_ids = [f.pk for f in dups if f.pk != canonical.pk]
        InvertGenus.objects.filter(family_id__in=non_canonical_ids).update(family=canonical)
        InvertAttribute.objects.filter(pk__in=non_canonical_ids).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0113_goi_schema_additions"),
    ]

    operations = [
        migrations.RunPython(populate_genus_group_of_interest, migrations.RunPython.noop),
        migrations.RunPython(populate_order_invert_class, migrations.RunPython.noop),
        migrations.RunPython(promote_goi_to_invert_attribute, migrations.RunPython.noop),
        migrations.RunPython(deduplicate_invert_order, migrations.RunPython.noop),
        migrations.RunPython(deduplicate_invert_family, migrations.RunPython.noop),
    ]
