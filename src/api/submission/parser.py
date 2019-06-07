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
    "get_site_id",
)


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
        sample_time=data.get("sample_time") or None,
        depth=data.get("depth"),
        visibility=data.get("visibility") or None,
        current=data.get("current") or None,
        relative_depth=data.get("relative_depth") or None,
        tide=data.get("tide") or None,
        notes=data.get("notes", ""),
    )


def get_fishbelt_transect_data(collect_record, sample_event_id=None):
    data = collect_record.data or dict()
    fishbelt_transect_data = data.get("fishbelt_transect") or dict()
    size_bin = fishbelt_transect_data.get("size_bin")

    # If size_bin isn't in the fishbelt_transect
    # check the legacy location in observations
    # TODO: This should be removed in a future
    # iteration
    if size_bin is None:
        obs = get_obsbeltfish_data(collect_record)
        for ob in obs:
            ob_size_bin = ob.get("size_bin")
            if ob_size_bin is not None:
                size_bin = ob_size_bin
                break

    return dict(
        sample_event=sample_event_id,
        number=fishbelt_transect_data.get("number"),
        label=fishbelt_transect_data.get("label") or "",
        width=fishbelt_transect_data.get("width"),
        len_surveyed=fishbelt_transect_data.get("len_surveyed"),
        reef_slope=fishbelt_transect_data.get("reef_slope"),
        size_bin=size_bin,
        collect_record_id=collect_record.id
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
                size=observation.get("size"),
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
        reef_slope=benthic_transect_data.get("reef_slope"),
        collect_record_id=collect_record.id
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
                interval=observation.get("interval"),
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
                interval=observation.get("interval"),
                notes=observation.get("notes", ""),
            )
        )

    return observations_data


def get_quadrat_collection_data(collect_record, sample_event_id=None):
    data = collect_record.data
    quadrat_collection_data = data.get("quadrat_collection") or dict()
    return dict(
        sample_event=sample_event_id,
        quadrat_size= quadrat_collection_data.get("quadrat_size"),
        collect_record_id=collect_record.id
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
