import re

from django.db import migrations

# Explicit rename map for all InvertGroupOfInterest names: original -> lowercased form.
# Acronyms (COTS) intentionally preserved.
GOI_RENAMES = {
    "Conchs": "conchs",
    "Corallivorous snails": "corallivorous snails",
    "Crabs / Shrimps": "crabs / shrimps",
    "Crown-of-thorns starfish (COTS)": "crown-of-thorns starfish (COTS)",
    "Giant clams": "giant clams",
    "Lobsters": "lobsters",
    "Octopus": "octopus",
    "Other invertebrates": "other invertebrates",
    "Pearl oysters": "pearl oysters",
    "Polychaete worms": "polychaete worms",
    "Sea cucumbers": "sea cucumbers",
    "Sea urchins": "sea urchins",
    "Triton's trumpets": "triton's trumpets",
    "Trochus shells": "trochus shells",
    "Turban shells": "turban shells",
}

# Maps the parenthetical common name (as it appears in old InvertClass.name) to the
# canonical InvertGroupOfInterest.name after lowercasing.
PARENTHETICAL_TO_GOI = {
    "conchs": "conchs",
    "corallivorous snails": "corallivorous snails",
    "Triton's trumpets": "triton's trumpets",
    "trochus shells": "trochus shells",
    "turban shells": "turban shells",
    "crabs / shrimps": "crabs / shrimps",
    "lobsters": "lobsters",
    "octopus": "octopus",
    "crown-of-thorns starfish - COTS": "crown-of-thorns starfish (COTS)",
    "giant clams": "giant clams",
    "pearl oysters": "pearl oysters",
    "polychaete worms": "polychaete worms",
    "sea cucumbers": "sea cucumbers",
    "sea urchins": "sea urchins",
}

OTHER_INVERTEBRATES = "other invertebrates"


def _parse_class_name(name):
    """Return (scientific_name, goi_name) from an InvertClass.name.

    'Gastropoda (conchs)' -> ('Gastropoda', 'conchs')
    'Gastropoda'          -> ('Gastropoda', 'other invertebrates')
    """
    m = re.match(r"^(.+?)\s+\((.+)\)$", name.strip())
    if m:
        sci_name = m.group(1).strip()
        common = m.group(2).strip()
        goi_name = PARENTHETICAL_TO_GOI.get(common, OTHER_INVERTEBRATES)
    else:
        sci_name = name.strip()
        goi_name = OTHER_INVERTEBRATES
    return sci_name, goi_name


def migrate_macroinvertebrate_taxonomy(apps, schema_editor):
    InvertAttribute = apps.get_model("api", "InvertAttribute")
    InvertClass = apps.get_model("api", "InvertClass")
    InvertClassGroupOfInterest = apps.get_model("api", "InvertClassGroupOfInterest")
    InvertGroupOfInterest = apps.get_model("api", "InvertGroupOfInterest")
    InvertOrder = apps.get_model("api", "InvertOrder")

    # ------------------------------------------------------------------ #
    # Step 0: rename InvertGroupOfInterest entries to lowercase form.     #
    # ------------------------------------------------------------------ #
    for goi in InvertGroupOfInterest.objects.all():
        new_name = GOI_RENAMES.get(goi.name, goi.name)
        if new_name != goi.name:
            goi.name = new_name
            goi.save(update_fields=["name"])

    # ------------------------------------------------------------------ #
    # Step 1: capture the (scientific_name, goi_name) for every order     #
    # from the current InvertClass.name before we rename anything.        #
    # ------------------------------------------------------------------ #
    # order_id -> (scientific_name, goi_name)
    order_sci_goi = {}
    for order in InvertOrder.objects.select_related("invert_class"):
        sci_name, goi_name = _parse_class_name(order.invert_class.name)
        order_sci_goi[order.pk] = (sci_name, goi_name)

    # ------------------------------------------------------------------ #
    # Step 2: choose a canonical InvertClass record per scientific name.  #
    #                                                                      #
    # Prefer the plain record (no parenthetical) when one exists.         #
    # Otherwise pick the record whose full name sorts first.              #
    # ------------------------------------------------------------------ #
    # Build: sci_name -> list of InvertClass instances
    sci_to_classes = {}
    for ic in InvertClass.objects.all():
        sci_name, _ = _parse_class_name(ic.name)
        sci_to_classes.setdefault(sci_name, []).append(ic)

    # sci_name -> canonical InvertClass instance
    canonical = {}
    duplicates_to_delete = []  # InvertAttribute PKs of non-canonical classes

    for sci_name, classes in sci_to_classes.items():
        # Prefer the record whose stored name IS already the scientific name.
        plain = [c for c in classes if c.name.strip() == sci_name]
        canon = plain[0] if plain else sorted(classes, key=lambda c: c.name)[0]
        canonical[sci_name] = canon

        for c in classes:
            if c.pk != canon.pk:
                duplicates_to_delete.append(c.pk)  # InvertAttribute PK (MTI)

    # ------------------------------------------------------------------ #
    # Step 3: re-point InvertOrder.invert_class for duplicates to the     #
    # canonical record, then rename the canonical record.                 #
    # ------------------------------------------------------------------ #
    for order in InvertOrder.objects.all():
        sci_name, _ = order_sci_goi[order.pk]
        canon = canonical[sci_name]
        if order.invert_class_id != canon.pk:
            order.invert_class = canon
            order.save(update_fields=["invert_class"])

    # Rename canonical records to the bare scientific name.
    for sci_name, canon in canonical.items():
        if canon.name != sci_name:
            canon.name = sci_name
            canon.save(update_fields=["name"])

    # Delete non-canonical InvertClass records via their InvertAttribute parent
    # so that both the invert_attribute and invert_class rows are removed.
    InvertAttribute.objects.filter(pk__in=duplicates_to_delete).delete()

    # ------------------------------------------------------------------ #
    # Step 4: create InvertClassGroupOfInterest records.                  #
    # One per (canonical InvertClass, InvertGroupOfInterest) pair.        #
    # ------------------------------------------------------------------ #
    # Collect distinct (sci_name, goi_name) pairs from all orders.
    sci_goi_pairs = set(order_sci_goi.values())

    # Map goi_name -> InvertGroupOfInterest instance (names already lowercased above).
    goi_by_name = {goi.name: goi for goi in InvertGroupOfInterest.objects.all()}

    # sci_name + goi_name -> InvertClassGroupOfInterest instance
    class_goi_map = {}
    for sci_name, goi_name in sci_goi_pairs:
        canon = canonical[sci_name]
        goi = goi_by_name[goi_name]
        cgoi, _ = InvertClassGroupOfInterest.objects.get_or_create(
            invert_class=canon,
            group_of_interest=goi,
        )
        class_goi_map[(sci_name, goi_name)] = cgoi

    # ------------------------------------------------------------------ #
    # Step 5: populate InvertOrder.class_goi.                             #
    # ------------------------------------------------------------------ #
    for order in InvertOrder.objects.all():
        sci_name, goi_name = order_sci_goi[order.pk]
        order.class_goi = class_goi_map[(sci_name, goi_name)]
        order.save(update_fields=["class_goi"])


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0108_macroinvertebrate_schema2"),
    ]

    operations = [
        migrations.RunPython(migrate_macroinvertebrate_taxonomy, migrations.RunPython.noop),
    ]
