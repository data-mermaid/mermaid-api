from django.contrib.gis.db import models

from ..protocols.macroinvertebrate import InvertAttribute


class InvertAttributeView(InvertAttribute):
    sql = """
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_invert_attributes
AS
SELECT ia.id,
CASE
    WHEN isp.invertattribute_ptr_id IS NOT NULL THEN isp_g.name || ' ' || isp.name
    WHEN ige.invertattribute_ptr_id IS NOT NULL THEN ige.name
    WHEN ifam.invertattribute_ptr_id IS NOT NULL THEN ifam.name
    WHEN iord.invertattribute_ptr_id IS NOT NULL THEN iord.name
    WHEN iclass.invertattribute_ptr_id IS NOT NULL THEN iclass.name
    WHEN igoi.invertattribute_ptr_id IS NOT NULL THEN igoi.name
    ELSE NULL
END AS name,
CASE
    WHEN igoi.invertattribute_ptr_id IS NOT NULL THEN igoi.name
    WHEN ige.invertattribute_ptr_id IS NOT NULL THEN ige_goi.name
    WHEN isp.invertattribute_ptr_id IS NOT NULL THEN isp_g_goi.name
    WHEN ifam.invertattribute_ptr_id IS NOT NULL THEN (
        SELECT string_agg(DISTINCT goi.name, ', ' ORDER BY goi.name)
        FROM invert_genus ig
        JOIN invert_group_of_interest goi ON ig.group_of_interest_id = goi.invertattribute_ptr_id
        WHERE ig.family_id = ifam.invertattribute_ptr_id
    )
    WHEN iord.invertattribute_ptr_id IS NOT NULL THEN (
        SELECT string_agg(DISTINCT goi.name, ', ' ORDER BY goi.name)
        FROM invert_genus ig
        JOIN invert_family f ON ig.family_id = f.invertattribute_ptr_id
        JOIN invert_group_of_interest goi ON ig.group_of_interest_id = goi.invertattribute_ptr_id
        WHERE f.order_id = iord.invertattribute_ptr_id
    )
    WHEN iclass.invertattribute_ptr_id IS NOT NULL THEN (
        SELECT string_agg(DISTINCT goi.name, ', ' ORDER BY goi.name)
        FROM invert_genus ig
        JOIN invert_family f ON ig.family_id = f.invertattribute_ptr_id
        JOIN invert_order o ON f.order_id = o.invertattribute_ptr_id
        JOIN invert_group_of_interest goi ON ig.group_of_interest_id = goi.invertattribute_ptr_id
        WHERE o.invert_class_id = iclass.invertattribute_ptr_id
    )
    ELSE NULL
END AS name_goi,
CASE
    WHEN iclass.invertattribute_ptr_id IS NOT NULL THEN iclass.name
    WHEN iord.invertattribute_ptr_id IS NOT NULL THEN iord_c.name
    WHEN ifam.invertattribute_ptr_id IS NOT NULL THEN ifam_o_c.name
    WHEN ige.invertattribute_ptr_id IS NOT NULL THEN ige_f_o_c.name
    WHEN isp.invertattribute_ptr_id IS NOT NULL THEN isp_g_f_o_c.name
    ELSE NULL
END AS name_class,
CASE
    WHEN iord.invertattribute_ptr_id IS NOT NULL THEN iord.name
    WHEN ifam.invertattribute_ptr_id IS NOT NULL THEN ifam_o.name
    WHEN ige.invertattribute_ptr_id IS NOT NULL THEN ige_f_o.name
    WHEN isp.invertattribute_ptr_id IS NOT NULL THEN isp_g_f_o.name
    ELSE NULL
END AS name_order,
CASE
    WHEN ifam.invertattribute_ptr_id IS NOT NULL THEN ifam.name
    WHEN ige.invertattribute_ptr_id IS NOT NULL THEN ige_f.name
    WHEN isp.invertattribute_ptr_id IS NOT NULL THEN isp_g_f.name
    ELSE NULL
END AS name_family,
CASE
    WHEN ige.invertattribute_ptr_id IS NOT NULL THEN ige.name
    WHEN isp.invertattribute_ptr_id IS NOT NULL THEN isp_g.name
    ELSE NULL
END AS name_genus,
CASE
    WHEN isp.invertattribute_ptr_id IS NOT NULL THEN isp.name
    ELSE NULL
END AS name_species

FROM invert_attribute ia
LEFT JOIN invert_group_of_interest igoi ON ia.id = igoi.invertattribute_ptr_id
LEFT JOIN invert_class iclass ON ia.id = iclass.invertattribute_ptr_id
LEFT JOIN invert_order iord ON ia.id = iord.invertattribute_ptr_id
LEFT JOIN invert_class iord_c ON iord.invert_class_id = iord_c.invertattribute_ptr_id
LEFT JOIN invert_family ifam ON ia.id = ifam.invertattribute_ptr_id
LEFT JOIN invert_order ifam_o ON ifam.order_id = ifam_o.invertattribute_ptr_id
LEFT JOIN invert_class ifam_o_c ON ifam_o.invert_class_id = ifam_o_c.invertattribute_ptr_id
LEFT JOIN invert_genus ige ON ia.id = ige.invertattribute_ptr_id
LEFT JOIN invert_group_of_interest ige_goi ON ige.group_of_interest_id = ige_goi.invertattribute_ptr_id
LEFT JOIN invert_family ige_f ON ige.family_id = ige_f.invertattribute_ptr_id
LEFT JOIN invert_order ige_f_o ON ige_f.order_id = ige_f_o.invertattribute_ptr_id
LEFT JOIN invert_class ige_f_o_c ON ige_f_o.invert_class_id = ige_f_o_c.invertattribute_ptr_id
LEFT JOIN invert_species isp ON ia.id = isp.invertattribute_ptr_id
LEFT JOIN invert_genus isp_g ON isp.genus_id = isp_g.invertattribute_ptr_id
LEFT JOIN invert_group_of_interest isp_g_goi ON isp_g.group_of_interest_id = isp_g_goi.invertattribute_ptr_id
LEFT JOIN invert_family isp_g_f ON isp_g.family_id = isp_g_f.invertattribute_ptr_id
LEFT JOIN invert_order isp_g_f_o ON isp_g_f.order_id = isp_g_f_o.invertattribute_ptr_id
LEFT JOIN invert_class isp_g_f_o_c ON isp_g_f_o.invert_class_id = isp_g_f_o_c.invertattribute_ptr_id

ORDER BY (
    CASE
        WHEN isp.invertattribute_ptr_id IS NOT NULL THEN isp_g.name || ' ' || isp.name
        WHEN ige.invertattribute_ptr_id IS NOT NULL THEN ige.name
        WHEN ifam.invertattribute_ptr_id IS NOT NULL THEN ifam.name
        WHEN iord.invertattribute_ptr_id IS NOT NULL THEN iord.name
        WHEN iclass.invertattribute_ptr_id IS NOT NULL THEN iclass.name
        WHEN igoi.invertattribute_ptr_id IS NOT NULL THEN igoi.name
        ELSE NULL
    END
);

CREATE UNIQUE INDEX invert_attributes_id
    ON mv_invert_attributes USING btree
    (id ASC NULLS LAST)
    WITH (deduplicate_items=True)
;
    """

    reverse_sql = """
      DROP MATERIALIZED VIEW IF EXISTS mv_invert_attributes;
    """

    name = models.CharField(max_length=200, null=True, blank=True)
    name_goi = models.CharField(max_length=200, null=True, blank=True)
    name_class = models.CharField(max_length=200, null=True, blank=True)
    name_order = models.CharField(max_length=200, null=True, blank=True)
    name_family = models.CharField(max_length=200, null=True, blank=True)
    name_genus = models.CharField(max_length=200, null=True, blank=True)
    name_species = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        db_table = "mv_invert_attributes"
        managed = False
