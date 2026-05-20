from django.db.models import Count

from ..models import InvertAttribute, InvertGenus


def invert_attribute_goi_distribution(invert_attribute_id):
    """Return {str(goi_pk): weight} for the given InvertAttribute pk.

    - GoI node:      {goi.pk: 1.0}
    - Species:       {species.genus.group_of_interest_id: 1.0}
    - Genus:         {genus.group_of_interest_id: 1.0}
    - Family/Order/Class: proportional over descendant genera by count
    """
    try:
        attr = InvertAttribute.objects.select_related(
            "invertgroupofinterest",
            "invertgenus",
            "invertspecies__genus",
            "invertfamily",
            "invertorder",
            "invertclass",
        ).get(pk=invert_attribute_id)
    except InvertAttribute.DoesNotExist:
        return {}

    if hasattr(attr, "invertgroupofinterest"):
        return {str(attr.pk): 1.0}

    if hasattr(attr, "invertspecies"):
        goi_id = attr.invertspecies.genus.group_of_interest_id
        return {str(goi_id): 1.0}

    if hasattr(attr, "invertgenus"):
        goi_id = attr.invertgenus.group_of_interest_id
        return {str(goi_id): 1.0}

    # For family/order/class, aggregate descendant genera by GoI.
    filter_kwarg = _genus_filter_kwarg(attr)
    if not filter_kwarg:
        return {}

    rows = (
        InvertGenus.objects.filter(**filter_kwarg)
        .values("group_of_interest_id")
        .annotate(n=Count("pk"))
    )
    total = sum(row["n"] for row in rows)
    if total == 0:
        return {}
    return {str(row["group_of_interest_id"]): row["n"] / total for row in rows}


def _genus_filter_kwarg(attr):
    if hasattr(attr, "invertfamily"):
        return {"family_id": attr.pk}
    if hasattr(attr, "invertorder"):
        return {"family__order_id": attr.pk}
    if hasattr(attr, "invertclass"):
        return {"family__order__invert_class_id": attr.pk}
    return None
