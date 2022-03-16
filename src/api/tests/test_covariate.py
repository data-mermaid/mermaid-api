
from api.covariates import CoralAtlasCovariate, VibrantOceansThreatsCovariate


def test_coral_atlas_covariate_with_map_assets(mock_covariate_server, alan_coral_atlas_map_assets):
    url = mock_covariate_server(alan_coral_atlas_map_assets)
    mock_coords = [(0, 0,)]

    cov = CoralAtlasCovariate()
    cov.api_url = url
    resp = cov.fetch(mock_coords)

    assert len(resp) == 1

    aca_benthic = resp[0]["covariates"]["aca_benthic"]
    assert len(aca_benthic) == 2

    for c in aca_benthic:
        assert c["name"] in ["Seagrass", "Sand"]


def test_coral_atlas_covariate_without_map_assets(mock_covariate_server, alan_coral_atlas_no_map_assets):
    url = mock_covariate_server(alan_coral_atlas_no_map_assets)
    mock_coords = [(0, 0,)]

    cov = CoralAtlasCovariate()
    cov.api_url = url
    resp = cov.fetch(mock_coords)

    assert resp[0]["covariates"]["aca_benthic"] is None
    assert resp[0]["covariates"]["aca_geomorphic"] is None


def test_vibrant_ocean_threats_covariate(load_allreef_sample):
    cov = VibrantOceansThreatsCovariate()
    coords = [(43.2676, -21.7859)]
    resp = cov.fetch(coords)

    assert len(resp) == 1

    covariates = resp[0]["covariates"]
    for col in VibrantOceansThreatsCovariate.COLUMNS:
        assert covariates[col] is not None


def test_vibrant_ocean_threats_covariate_no_response(load_allreef_sample):
    cov = VibrantOceansThreatsCovariate()
    coords = [(0, 0)]
    resp = cov.fetch(coords)

    assert len(resp) == 1

    covariates = resp[0]["covariates"]
    for col in VibrantOceansThreatsCovariate.COLUMNS:
        assert covariates[col] is None
