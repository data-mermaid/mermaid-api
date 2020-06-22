__all__ = (
    "get_benthic_transect_data",
    "get_fishbelt_transect_data",
    "get_management_id",
    "get_obs_colonies_bleached_data",
    "get_obs_quadrat_benthic_percent_data",
    "get_obsbeltfish_data",
    "get_obsbenthiclit_data",
    "get_obsbenthicpit_data",
    "get_observers_data",
    "get_obshabitatcomplexity_data",
    "get_quadrat_collection_data",
    "get_sample_event_data",
    "get_sample_event_id",
    "get_site_id",
)


def _cast_decimal_to_str(val):
    if val is None:
        return None

    return str(val)


def _extract_sample_event(collect_record):
    data = collect_record.data or dict()
    return data.get("sample_event") or dict()


def get_site_id(collect_record):
    data = _extract_sample_event(collect_record)
    return data.get("site")


def get_management_id(collect_record):
    data = _extract_sample_event(collect_record)
    return data.get("management")


def get_sample_event_data(collect_record, site_id=None, management_id=None):
    data = _extract_sample_event(collect_record)

    return dict(
        site=site_id or data.get("site") or None,
        management=management_id or data.get("management") or None,
        sample_date=data.get("sample_date") or None,
        notes=data.get("notes", ""),
    )


def get_sample_event_id(collect_record):
    data = collect_record.data or dict()
    return data.get("sample_event")


def get_fishbelt_transect_data(collect_record, sample_event_id=None):
    data = collect_record.data or dict()
    fishbelt_transect_data = data.get("fishbelt_transect") or dict()
    size_bin = fishbelt_transect_data.get("size_bin")


    return dict(
        sample_event=sample_event_id,
        number=fishbelt_transect_data.get("number"),
        label=fishbelt_transect_data.get("label") or "",
        width=fishbelt_transect_data.get("width"),
        len_surveyed=fishbelt_transect_data.get("len_surveyed"),
        reef_slope=fishbelt_transect_data.get("reef_slope") or None,
        size_bin=size_bin,
        collect_record_id=collect_record.id,
        sample_time=fishbelt_transect_data.get("sample_time") or None,
        depth=_cast_decimal_to_str(fishbelt_transect_data.get("depth")),
        visibility=fishbelt_transect_data.get("visibility") or None,
        current=fishbelt_transect_data.get("current") or None,
        relative_depth=fishbelt_transect_data.get("relative_depth") or None,
        tide=fishbelt_transect_data.get("tide") or None,
    )



def get_observers_data(collect_record, transect_method_id=None):
    observer_data = []
    data = collect_record.data
    observers = data.get("observers") or []
    for observer in observers:
        observer_data.append(
            dict(transectmethod=transect_method_id, profile=observer.get("profile"))
        )

    return observer_data


def get_obsbeltfish_data(collect_record, belt_fish_id=None):
    observations_data = []
    data = collect_record.data or dict()
    observations = data.get("obs_belt_fishes") or []
    for observation in observations:
        observations_data.append(
            dict(
                beltfish=belt_fish_id,
                fish_attribute=observation.get("fish_attribute"),
                count=observation.get("count"),
                size=_cast_decimal_to_str(observation.get("size")),
                size_bin=observation.get("size_bin"),
                notes=observation.get("notes", ""),
            )
        )

    return observations_data


def get_benthic_transect_data(collect_record, sample_event_id=None):
    data = collect_record.data
    benthic_transect_data = data.get("benthic_transect") or dict()
    return dict(
        sample_event=sample_event_id,
        number=benthic_transect_data.get("number"),
        label= benthic_transect_data.get("label") or "",
        len_surveyed=benthic_transect_data.get("len_surveyed"),
        reef_slope=benthic_transect_data.get("reef_slope") or None,
        collect_record_id=collect_record.id,
        sample_time=benthic_transect_data.get("sample_time") or None,
        depth=_cast_decimal_to_str(benthic_transect_data.get("depth")),
        visibility=benthic_transect_data.get("visibility") or None,
        current=benthic_transect_data.get("current") or None,
        relative_depth=benthic_transect_data.get("relative_depth") or None,
        tide=benthic_transect_data.get("tide") or None,
    )


def get_obsbenthiclit_data(collect_record, benthic_lit_id=None):
    observations_data = []
    data = collect_record.data or dict()
    observations = data.get("obs_benthic_lits") or []
    for observation in observations:
        observations_data.append(
            dict(
                benthiclit=benthic_lit_id,
                attribute=observation.get("attribute"),
                growth_form=observation.get("growth_form"),
                length=observation.get("length"),
                notes=observation.get("notes", ""),
            )
        )

    return observations_data


def get_obsbenthicpit_data(collect_record, benthic_pit_id=None):
    observations_data = []
    data = collect_record.data or dict()
    observations = data.get("obs_benthic_pits") or []
    for observation in observations:
        observations_data.append(
            dict(
                benthicpit=benthic_pit_id,
                attribute=observation.get("attribute"),
                growth_form=observation.get("growth_form"),
                interval=_cast_decimal_to_str(observation.get("interval")),
                notes=observation.get("notes", ""),
            )
        )

    return observations_data


def get_obshabitatcomplexity_data(collect_record, habitatcomplexity_id=None):
    observations_data = []
    data = collect_record.data or dict()
    observations = data.get("obs_habitat_complexities") or []
    for observation in observations:
        observations_data.append(
            dict(
                habitatcomplexity=habitatcomplexity_id,
                score=observation.get("score"),
                interval=_cast_decimal_to_str(observation.get("interval")),
                notes=observation.get("notes", ""),
            )
        )

    return observations_data


def get_quadrat_collection_data(collect_record, sample_event_id=None):
    data = collect_record.data
    quadrat_collection_data = data.get("quadrat_collection") or dict()
    return dict(
        sample_event=sample_event_id,
        quadrat_size=_cast_decimal_to_str(quadrat_collection_data.get("quadrat_size")),
        collect_record_id=collect_record.id,
        sample_time=quadrat_collection_data.get("sample_time") or None,
        depth=_cast_decimal_to_str(quadrat_collection_data.get("depth")),
        visibility=quadrat_collection_data.get("visibility") or None,
        current=quadrat_collection_data.get("current") or None,
        relative_depth=quadrat_collection_data.get("relative_depth") or None,
        tide=quadrat_collection_data.get("tide") or None,
    )


def get_obs_quadrat_benthic_percent_data(collect_record, bleaching_quadrat_collection_id=None):
    observations_data = []
    data = collect_record.data or dict()
    observations = data.get("obs_quadrat_benthic_percent") or []
    for observation in observations:
        observations_data.append(
            dict(
                bleachingquadratcollection=bleaching_quadrat_collection_id,
                quadrat_number=observation.get("quadrat_number"),
                percent_algae=observation.get("percent_algae"),
                percent_hard=observation.get("percent_hard"),
                percent_soft=observation.get("percent_soft")
            )
        )

    return observations_data


def get_obs_colonies_bleached_data(collect_record, bleaching_quadrat_collection_id=None):
    observations_data = []
    data = collect_record.data or dict()
    observations = data.get("obs_colonies_bleached") or []
    for observation in observations:
        observations_data.append(
            dict(
                bleachingquadratcollection=bleaching_quadrat_collection_id,
                attribute=observation.get("attribute"),
                growth_form=observation.get("growth_form"),
                count_normal=observation.get("count_normal"),
                count_pale=observation.get("count_pale") ,
                count_20=observation.get("count_20"),
                count_50=observation.get("count_50"),
                count_80=observation.get("count_80"),
                count_100=observation.get("count_100"),
                count_dead=observation.get("count_dead"),
            )
        )

    return observations_data
