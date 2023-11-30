SELECT
    "belt_fish_su_sm"."id",
    "belt_fish_su_sm"."project_id",
    "belt_fish_su_sm"."project_name",
    "belt_fish_su_sm"."project_status",
    "belt_fish_su_sm"."project_notes",
    "belt_fish_su_sm"."project_admins",
    "belt_fish_su_sm"."contact_link",
    "belt_fish_su_sm"."tags",
    "belt_fish_su_sm"."site_id",
    "belt_fish_su_sm"."site_name",
    "belt_fish_su_sm"."location" :: bytea,
    "belt_fish_su_sm"."longitude",
    "belt_fish_su_sm"."latitude",
    "belt_fish_su_sm"."site_notes",
    "belt_fish_su_sm"."country_id",
    "belt_fish_su_sm"."country_name",
    "belt_fish_su_sm"."reef_type",
    "belt_fish_su_sm"."reef_zone",
    "belt_fish_su_sm"."reef_exposure",
    "belt_fish_su_sm"."management_id",
    "belt_fish_su_sm"."management_name",
    "belt_fish_su_sm"."management_name_secondary",
    "belt_fish_su_sm"."management_est_year",
    "belt_fish_su_sm"."management_size",
    "belt_fish_su_sm"."management_parties",
    "belt_fish_su_sm"."management_compliance",
    "belt_fish_su_sm"."management_rules",
    "belt_fish_su_sm"."management_notes",
    "belt_fish_su_sm"."sample_date",
    "belt_fish_su_sm"."sample_event_id",
    "belt_fish_su_sm"."sample_event_notes",
    "belt_fish_su_sm"."depth",
    "belt_fish_su_sm"."sample_unit_ids",
    "belt_fish_su_sm"."label",
    "belt_fish_su_sm"."relative_depth",
    "belt_fish_su_sm"."sample_time",
    "belt_fish_su_sm"."observers",
    "belt_fish_su_sm"."current_name",
    "belt_fish_su_sm"."tide_name",
    "belt_fish_su_sm"."visibility_name",
    "belt_fish_su_sm"."sample_unit_notes",
    "belt_fish_su_sm"."total_abundance",
    "belt_fish_su_sm"."transect_number",
    "belt_fish_su_sm"."transect_len_surveyed",
    "belt_fish_su_sm"."transect_width_name",
    "belt_fish_su_sm"."reef_slope",
    "belt_fish_su_sm"."size_bin",
    "belt_fish_su_sm"."biomass_kgha",
    "belt_fish_su_sm"."biomass_kgha_trophic_group",
    "belt_fish_su_sm"."biomass_kgha_fish_family",
    "belt_fish_su_sm"."data_policy_beltfish",
    "belt_fish_su_sm"."pseudosu_id",
    "belt_fish_su_sm"."biomass_kgha_trophic_group_zeroes",
    "belt_fish_su_sm"."biomass_kgha_fish_family_zeroes"
FROM
    (
        WITH beltfish_obs AS (
            WITH se AS (
                WITH tags AS MATERIALIZED (
                    SELECT
                        project_1.id,
                        jsonb_agg(
                            jsonb_build_object('id', t_1.id, 'name', t_1.name)
                        ) AS tags
                    FROM
                        api_uuidtaggeditem ti
                        JOIN django_content_type ct ON ti.content_type_id = ct.id
                        JOIN project project_1 ON ti.object_id = project_1.id
                        JOIN api_tag t_1 ON ti.tag_id = t_1.id
                    WHERE
                        ct.app_label :: text = 'api' :: text
                        AND ct.model :: text = 'project' :: text
                    GROUP BY
                        project_1.id
                ),
                project_admins AS MATERIALIZED (
                    SELECT
                        project_id,
                        jsonb_agg(
                            jsonb_build_object(
                                'id',
                                p.id,
                                'name',
                                (
                                    COALESCE(p.first_name, '' :: character varying) :: text || ' ' :: text
                                ) || COALESCE(p.last_name, '' :: character varying) :: text
                            )
                        ) AS project_admins
                    FROM
                        project_profile pp
                        INNER JOIN profile p ON (pp.profile_id = p.id)
                    WHERE
                        project_id = '75ef7a5a-c770-4ca6-b9f8-830cab74e425' :: uuid
                        AND role >= 90
                    GROUP BY
                        project_id
                ),
                parties AS MATERIALIZED (
                    SELECT
                        mps.management_id,
                        jsonb_agg(
                            mp.name
                            ORDER BY
                                mp.name
                        ) AS parties
                    FROM
                        management_parties mps
                        INNER JOIN management_party mp ON mps.managementparty_id = mp.id
                        INNER JOIN management ON (management.id = mps.management_id)
                    WHERE
                        management.project_id = '75ef7a5a-c770-4ca6-b9f8-830cab74e425' :: uuid
                    GROUP BY
                        mps.management_id
                )
                SELECT
                    project.id AS project_id,
                    project.name AS project_name,
                    project.status AS project_status,
                    project.notes AS project_notes,
                    'https://datamermaid.org/contact-project?project_id=' :: text || COALESCE(project.id :: text, '' :: text) AS contact_link,
                    project_admins.project_admins,
                    tags.tags,
                    se.site_id,
                    site.name AS site_name,
                    site.location,
                    ST_X(site.location) AS longitude,
                    ST_Y(site.location) AS latitude,
                    site.notes AS site_notes,
                    country.id AS country_id,
                    country.name AS country_name,
                    rt.name AS reef_type,
                    rz.name AS reef_zone,
                    re.name AS reef_exposure,
                    m.id AS management_id,
                    m.name AS management_name,
                    m.name_secondary AS management_name_secondary,
                    m.est_year AS management_est_year,
                    m.size AS management_size,
                    parties.parties AS management_parties,
                    mc.name AS management_compliance,
                    array_to_json(
                        array_remove(
                            ARRAY [
            CASE
                WHEN m.no_take THEN 'no take'::text
                ELSE NULL::text
            END,
            CASE
                WHEN m.open_access THEN 'open access'::text
                ELSE NULL::text
            END,
            CASE
                WHEN m.gear_restriction THEN 'gear restriction'::text
                ELSE NULL::text
            END,
            CASE
                WHEN m.periodic_closure THEN 'periodic closure'::text
                ELSE NULL::text
            END,
            CASE
                WHEN m.size_limits THEN 'size limits'::text
                ELSE NULL::text
            END,
            CASE
                WHEN m.species_restriction THEN 'species restriction'::text
                ELSE NULL::text
            END,
            CASE
                WHEN m.access_restriction THEN 'access restriction'::text
                ELSE NULL::text
            END],
                            NULL :: text
                        )
                    ) :: jsonb AS management_rules,
                    m.notes AS management_notes,
                    se.id AS sample_event_id,
                    se.sample_date,
                    se.notes AS sample_event_notes,
                    CASE
                        WHEN project.data_policy_beltfish = 10 THEN 'private' :: text
                        WHEN project.data_policy_beltfish = 50 THEN 'public summary' :: text
                        WHEN project.data_policy_beltfish = 100 THEN 'public' :: text
                        ELSE '' :: text
                    END AS data_policy_beltfish,
                    CASE
                        WHEN project.data_policy_benthiclit = 10 THEN 'private' :: text
                        WHEN project.data_policy_benthiclit = 50 THEN 'public summary' :: text
                        WHEN project.data_policy_benthiclit = 100 THEN 'public' :: text
                        ELSE '' :: text
                    END AS data_policy_benthiclit,
                    CASE
                        WHEN project.data_policy_benthicpit = 10 THEN 'private' :: text
                        WHEN project.data_policy_benthicpit = 50 THEN 'public summary' :: text
                        WHEN project.data_policy_benthicpit = 100 THEN 'public' :: text
                        ELSE '' :: text
                    END AS data_policy_benthicpit,
                    CASE
                        WHEN project.data_policy_habitatcomplexity = 10 THEN 'private' :: text
                        WHEN project.data_policy_habitatcomplexity = 50 THEN 'public summary' :: text
                        WHEN project.data_policy_habitatcomplexity = 100 THEN 'public' :: text
                        ELSE '' :: text
                    END AS data_policy_habitatcomplexity,
                    CASE
                        WHEN project.data_policy_bleachingqc = 10 THEN 'private' :: text
                        WHEN project.data_policy_bleachingqc = 50 THEN 'public summary' :: text
                        WHEN project.data_policy_bleachingqc = 100 THEN 'public' :: text
                        ELSE '' :: text
                    END AS data_policy_bleachingqc,
                    CASE
                        WHEN project.data_policy_benthicpqt = 10 THEN 'private' :: text
                        WHEN project.data_policy_benthicpqt = 50 THEN 'public summary' :: text
                        WHEN project.data_policy_benthicpqt = 100 THEN 'public' :: text
                        ELSE '' :: text
                    END AS data_policy_benthicpqt
                FROM
                    sample_event se
                    JOIN site ON se.site_id = site.id
                    JOIN project ON site.project_id = project.id
                    LEFT JOIN project_admins ON (project.id = project_admins.project_id)
                    LEFT JOIN tags ON project.id = tags.id
                    JOIN country ON site.country_id = country.id
                    LEFT JOIN api_reeftype rt ON site.reef_type_id = rt.id
                    LEFT JOIN api_reefzone rz ON site.reef_zone_id = rz.id
                    LEFT JOIN api_reefexposure re ON site.exposure_id = re.id
                    JOIN management m ON se.management_id = m.id
                    LEFT JOIN management_compliance mc ON m.compliance_id = mc.id
                    LEFT JOIN parties ON m.id = parties.management_id
                WHERE
                    1 = 1
                    AND project.id = '75ef7a5a-c770-4ca6-b9f8-830cab74e425' :: uuid
            ),
            pseudosu_su AS MATERIALIZED (
                SELECT
                    pseudosu_id,
                    UNNEST(sample_unit_ids) AS sample_unit_id
                FROM
                    (
                        SELECT
                            uuid_generate_v4() AS pseudosu_id,
                            array_agg(DISTINCT su.id) AS sample_unit_ids
                        FROM
                            transect_belt_fish su
                            JOIN se ON su.sample_event_id = se.sample_event_id
                        GROUP BY
                            su.sample_event_id,
                            su.depth,
                            su.number,
                            su.len_surveyed
                    ) pseudosu
            )
            SELECT
                o.id,
                pseudosu_id,
                se.project_id,
                se.project_name,
                se.project_status,
                se.project_notes,
                se.project_admins,
                se.contact_link,
                se.tags,
                se.site_id,
                se.site_name,
                se.location,
                se.longitude,
                se.latitude,
                se.site_notes,
                se.country_id,
                se.country_name,
                se.reef_type,
                se.reef_zone,
                se.reef_exposure,
                se.management_id,
                se.management_name,
                se.management_name_secondary,
                se.management_est_year,
                se.management_size,
                se.management_parties,
                se.management_compliance,
                se.management_rules,
                se.management_notes,
                se.sample_event_id,
                se.sample_date,
                se.sample_event_notes,
                su.id AS sample_unit_id,
                su.depth,
                su.label,
                r.name AS relative_depth,
                su.sample_time,
                observers.observers,
                c.name AS current_name,
                t.name AS tide_name,
                v.name AS visibility_name,
                su.notes AS sample_unit_notes,
                se.data_policy_beltfish,
                su.number AS transect_number,
                su.len_surveyed AS transect_len_surveyed,
                rs.name AS reef_slope,
                w.name AS transect_width_name,
                wc.val AS assigned_transect_width_m,
                f.id_family AS id_family,
                f.id_genus AS id_genus,
                f.id_species AS id_species,
                f.name_family AS fish_family,
                f.name_genus AS fish_genus,
                f.name AS fish_taxon,
                f.trophic_group,
                f.trophic_level,
                f.functional_group,
                f.vulnerability,
                f.biomass_constant_a,
                f.biomass_constant_b,
                f.biomass_constant_c,
                sb.val AS size_bin,
                o.size,
                o.count,
                ROUND(
                    (10 * o.count) :: numeric * f.biomass_constant_a * power(
                        (o.size * f.biomass_constant_c) :: float,
                        f.biomass_constant_b :: float
                    ) :: numeric / (su.len_surveyed * wc.val) :: numeric,
                    2
                ) :: numeric AS biomass_kgha,
                o.notes AS observation_notes
            FROM
                obs_transectbeltfish o
                RIGHT JOIN transectmethod_transectbeltfish tt ON o.beltfish_id = tt.transectmethod_ptr_id
                JOIN transect_belt_fish su ON tt.transect_id = su.id
                JOIN se ON su.sample_event_id = se.sample_event_id
                JOIN pseudosu_su ON (su.id = pseudosu_su.sample_unit_id)
                LEFT JOIN vw_fish_attributes f ON o.fish_attribute_id = f.id
                JOIN api_belttransectwidth w ON su.width_id = w.id
                JOIN api_belttransectwidthcondition wc ON (
                    w.id = wc.belttransectwidth_id
                    AND (
                        (
                            (
                                wc.operator = '<'
                                AND o.size < wc.size
                            )
                            OR (
                                wc.operator IS NULL
                                AND wc.size IS NULL
                            )
                        )
                        OR (
                            (
                                wc.operator = '<='
                                AND o.size <= wc.size
                            )
                            OR (
                                wc.operator IS NULL
                                AND wc.size IS NULL
                            )
                        )
                        OR (
                            (
                                wc.operator = '>'
                                AND o.size > wc.size
                            )
                            OR (
                                wc.operator IS NULL
                                AND wc.size IS NULL
                            )
                        )
                        OR (
                            (
                                wc.operator = '>='
                                AND o.size >= wc.size
                            )
                            OR (
                                wc.operator IS NULL
                                AND wc.size IS NULL
                            )
                        )
                        OR (
                            (
                                wc.operator = '=='
                                AND o.size = wc.size
                            )
                            OR (
                                wc.operator IS NULL
                                AND wc.size IS NULL
                            )
                        )
                        OR (
                            (
                                wc.operator = '!='
                                AND o.size != wc.size
                            )
                            OR (
                                wc.operator IS NULL
                                AND wc.size IS NULL
                            )
                        )
                    )
                )
                JOIN (
                    SELECT
                        tt_1.transect_id,
                        jsonb_agg(
                            jsonb_build_object(
                                'id',
                                p.id,
                                'name',
                                (
                                    COALESCE(p.first_name, '' :: character varying) :: text || ' ' :: text
                                ) || COALESCE(p.last_name, '' :: character varying) :: text
                            )
                        ) AS observers
                    FROM
                        observer o1
                        JOIN profile p ON o1.profile_id = p.id
                        JOIN transectmethod tm ON o1.transectmethod_id = tm.id
                        JOIN transectmethod_transectbeltfish tt_1 ON tm.id = tt_1.transectmethod_ptr_id
                        JOIN transect_belt_fish as tbf ON tt_1.transect_id = tbf.id
                        JOIN se ON tbf.sample_event_id = se.sample_event_id
                    GROUP BY
                        tt_1.transect_id
                ) observers ON su.id = observers.transect_id
                LEFT JOIN api_current c ON su.current_id = c.id
                LEFT JOIN api_tide t ON su.tide_id = t.id
                LEFT JOIN api_visibility v ON su.visibility_id = v.id
                LEFT JOIN api_relativedepth r ON su.relative_depth_id = r.id
                LEFT JOIN api_fishsizebin sb ON su.size_bin_id = sb.id
                LEFT JOIN api_reefslope rs ON su.reef_slope_id = rs.id
        ),
        beltfish_su_tg_all AS MATERIALIZED (
            SELECT
                pseudosu_id,
                fish_group_trophic.name AS trophic_group
            FROM
                fish_group_trophic
                CROSS JOIN beltfish_obs
            GROUP BY
                pseudosu_id,
                fish_group_trophic.name
        ),
        beltfish_su_tg AS MATERIALIZED (
            SELECT
                pseudosu_id,
                trophic_group,
                COALESCE(SUM(biomass_kgha), 0 :: numeric) AS biomass_kgha
            FROM
                beltfish_obs
            GROUP BY
                pseudosu_id,
                trophic_group
        ),
        beltfish_su_family_all AS MATERIALIZED (
            SELECT
                pseudosu_id,
                fish_family.name AS fish_family
            FROM
                fish_family
                CROSS JOIN beltfish_obs
            GROUP BY
                pseudosu_id,
                fish_family.name
        ),
        beltfish_su_family AS MATERIALIZED (
            SELECT
                pseudosu_id,
                fish_family,
                COALESCE(SUM(biomass_kgha), 0 :: numeric) AS biomass_kgha
            FROM
                beltfish_obs
            GROUP BY
                pseudosu_id,
                fish_family
        ),
        beltfish_tg AS MATERIALIZED (
            SELECT
                beltfish_su_tg.pseudosu_id,
                jsonb_object_agg(
                    CASE
                        WHEN beltfish_su_tg.trophic_group IS NULL THEN 'other' :: character varying
                        ELSE beltfish_su_tg.trophic_group
                    END,
                    ROUND(beltfish_su_tg.biomass_kgha, 2)
                ) AS biomass_kgha_trophic_group,
                jsonb_object_agg(
                    beltfish_su_tg_zeroes.trophic_group,
                    ROUND(beltfish_su_tg_zeroes.biomass_kgha, 2)
                ) AS biomass_kgha_trophic_group_zeroes
            FROM
                beltfish_su_tg
                INNER JOIN (
                    SELECT
                        beltfish_su_tg_all.pseudosu_id,
                        beltfish_su_tg_all.trophic_group,
                        COALESCE(beltfish_su_tg.biomass_kgha, 0) AS biomass_kgha
                    FROM
                        beltfish_su_tg_all
                        LEFT JOIN beltfish_su_tg ON(
                            beltfish_su_tg_all.pseudosu_id = beltfish_su_tg.pseudosu_id
                            AND beltfish_su_tg_all.trophic_group = beltfish_su_tg.trophic_group
                        )
                ) beltfish_su_tg_zeroes ON(
                    beltfish_su_tg.pseudosu_id = beltfish_su_tg_zeroes.pseudosu_id
                )
            GROUP BY
                beltfish_su_tg.pseudosu_id
        ),
        beltfish_families AS MATERIALIZED (
            SELECT
                beltfish_su_family.pseudosu_id,
                jsonb_object_agg(
                    CASE
                        WHEN beltfish_su_family.fish_family IS NULL THEN 'other' :: character varying
                        ELSE beltfish_su_family.fish_family
                    END,
                    ROUND(beltfish_su_family.biomass_kgha, 2)
                ) AS biomass_kgha_fish_family,
                jsonb_object_agg(
                    beltfish_su_family_zeroes.fish_family,
                    ROUND(beltfish_su_family_zeroes.biomass_kgha, 2)
                ) AS biomass_kgha_fish_family_zeroes
            FROM
                beltfish_su_family
                INNER JOIN (
                    SELECT
                        beltfish_su_family_all.pseudosu_id,
                        beltfish_su_family_all.fish_family,
                        COALESCE(beltfish_su_family.biomass_kgha, 0) AS biomass_kgha
                    FROM
                        beltfish_su_family_all
                        LEFT JOIN beltfish_su_family ON(
                            beltfish_su_family_all.pseudosu_id = beltfish_su_family.pseudosu_id
                            AND beltfish_su_family_all.fish_family = beltfish_su_family.fish_family
                        )
                ) beltfish_su_family_zeroes ON(
                    beltfish_su_family.pseudosu_id = beltfish_su_family_zeroes.pseudosu_id
                )
            GROUP BY
                beltfish_su_family.pseudosu_id
        ),
        beltfish_observers AS (
            SELECT
                pseudosu_id,
                jsonb_agg(DISTINCT observer) AS observers
            FROM
                (
                    SELECT
                        pseudosu_id,
                        jsonb_array_elements(observers) AS observer
                    FROM
                        beltfish_obs
                    GROUP BY
                        pseudosu_id,
                        observers
                ) beltfish_obs_obs
            GROUP BY
                pseudosu_id
        )
        SELECT
            NULL AS id,
            beltfish_su.pseudosu_id,
            project_id,
            project_name,
            project_status,
            project_notes,
            project_admins,
            contact_link,
            tags,
            site_id,
            site_name,
            location,
            longitude,
            latitude,
            site_notes,
            country_id,
            country_name,
            reef_type,
            reef_zone,
            reef_exposure,
            management_id,
            management_name,
            management_name_secondary,
            management_est_year,
            management_size,
            management_parties,
            management_compliance,
            management_rules,
            management_notes,
            sample_event_id,
            sample_date,
            sample_event_notes,
            depth,
            transect_number,
            transect_len_surveyed,
            data_policy_beltfish,
            beltfish_su.sample_unit_ids,
            label,
            relative_depth,
            sample_time,
            observers,
            current_name,
            tide_name,
            visibility_name,
            sample_unit_notes,
            reef_slope,
            transect_width_name,
            size_bin,
            total_abundance,
            biomass_kgha,
            biomass_kgha_trophic_group,
            biomass_kgha_trophic_group_zeroes,
            biomass_kgha_fish_family,
            biomass_kgha_fish_family_zeroes
        FROM
            (
                SELECT
                    pseudosu_id,
                    jsonb_agg(DISTINCT sample_unit_id) AS sample_unit_ids,
                    COALESCE(SUM(beltfish_obs.count), 0) AS total_abundance,
                    COALESCE(SUM(beltfish_obs.biomass_kgha), 0) AS biomass_kgha,
                    beltfish_obs.project_id,
                    beltfish_obs.project_name,
                    beltfish_obs.project_status,
                    beltfish_obs.project_notes,
                    beltfish_obs.project_admins,
                    beltfish_obs.contact_link,
                    beltfish_obs.tags,
                    beltfish_obs.site_id,
                    beltfish_obs.site_name,
                    beltfish_obs.location,
                    beltfish_obs.longitude,
                    beltfish_obs.latitude,
                    beltfish_obs.site_notes,
                    beltfish_obs.country_id,
                    beltfish_obs.country_name,
                    beltfish_obs.reef_type,
                    beltfish_obs.reef_zone,
                    beltfish_obs.reef_exposure,
                    beltfish_obs.management_id,
                    beltfish_obs.management_name,
                    beltfish_obs.management_name_secondary,
                    beltfish_obs.management_est_year,
                    beltfish_obs.management_size,
                    beltfish_obs.management_parties,
                    beltfish_obs.management_compliance,
                    beltfish_obs.management_rules,
                    beltfish_obs.management_notes,
                    beltfish_obs.sample_event_id,
                    beltfish_obs.sample_date,
                    beltfish_obs.sample_event_notes,
                    beltfish_obs.depth,
                    beltfish_obs.transect_number,
                    beltfish_obs.transect_len_surveyed,
                    beltfish_obs.data_policy_beltfish,
                    string_agg(
                        DISTINCT label :: text,
                        ', ' :: text
                        ORDER BY
                            (label :: text)
                    ) AS label,
                    string_agg(
                        DISTINCT relative_depth :: text,
                        ', ' :: text
                        ORDER BY
                            (relative_depth :: text)
                    ) AS relative_depth,
                    string_agg(
                        DISTINCT sample_time :: text,
                        ', ' :: text
                        ORDER BY
                            (sample_time :: text)
                    ) AS sample_time,
                    string_agg(
                        DISTINCT current_name :: text,
                        ', ' :: text
                        ORDER BY
                            (current_name :: text)
                    ) AS current_name,
                    string_agg(
                        DISTINCT tide_name :: text,
                        ', ' :: text
                        ORDER BY
                            (tide_name :: text)
                    ) AS tide_name,
                    string_agg(
                        DISTINCT visibility_name :: text,
                        ', ' :: text
                        ORDER BY
                            (visibility_name :: text)
                    ) AS visibility_name,
                    string_agg(DISTINCT sample_unit_notes :: text, '

 ' :: text) AS sample_unit_notes,
                    string_agg(
                        DISTINCT reef_slope :: text,
                        ', ' :: text
                        ORDER BY
                            (reef_slope :: text)
                    ) AS reef_slope,
                    string_agg(
                        DISTINCT transect_width_name :: text,
                        ', ' :: text
                        ORDER BY
                            (transect_width_name :: text)
                    ) AS transect_width_name,
                    string_agg(
                        DISTINCT size_bin :: text,
                        ', ' :: text
                        ORDER BY
                            (size_bin :: text)
                    ) AS size_bin
                FROM
                    beltfish_obs
                GROUP BY
                    pseudosu_id,
                    beltfish_obs.project_id,
                    beltfish_obs.project_name,
                    beltfish_obs.project_status,
                    beltfish_obs.project_notes,
                    beltfish_obs.project_admins,
                    beltfish_obs.contact_link,
                    beltfish_obs.tags,
                    beltfish_obs.site_id,
                    beltfish_obs.site_name,
                    beltfish_obs.location,
                    beltfish_obs.longitude,
                    beltfish_obs.latitude,
                    beltfish_obs.site_notes,
                    beltfish_obs.country_id,
                    beltfish_obs.country_name,
                    beltfish_obs.reef_type,
                    beltfish_obs.reef_zone,
                    beltfish_obs.reef_exposure,
                    beltfish_obs.management_id,
                    beltfish_obs.management_name,
                    beltfish_obs.management_name_secondary,
                    beltfish_obs.management_est_year,
                    beltfish_obs.management_size,
                    beltfish_obs.management_parties,
                    beltfish_obs.management_compliance,
                    beltfish_obs.management_rules,
                    beltfish_obs.management_notes,
                    beltfish_obs.sample_event_id,
                    beltfish_obs.sample_date,
                    beltfish_obs.sample_event_notes,
                    beltfish_obs.depth,
                    beltfish_obs.transect_number,
                    beltfish_obs.transect_len_surveyed,
                    beltfish_obs.data_policy_beltfish
            ) beltfish_su
            INNER JOIN beltfish_tg ON (
                beltfish_su.pseudosu_id = beltfish_tg.pseudosu_id
            )
            INNER JOIN beltfish_families ON (
                beltfish_su.pseudosu_id = beltfish_families.pseudosu_id
            )
            INNER JOIN beltfish_observers ON (
                beltfish_su.pseudosu_id = beltfish_observers.pseudosu_id
            )
    ) belt_fish_su_sm