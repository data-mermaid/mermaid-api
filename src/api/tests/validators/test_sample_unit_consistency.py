from datetime import timedelta

from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations import OK, WARN
from api.submission.validations.validators import (
    DifferentNumPointsPerQuadratValidator,
    DifferentNumQuadratsValidator,
    DifferentQuadratSizeValidator,
    DifferentTransectLengthValidator,
    DifferentTransectWidthValidator,
)

# ==================== DifferentNumQuadratsValidator tests ====================


def _get_num_quadrats_validator():
    return DifferentNumQuadratsValidator(
        site_path="data.sample_event.site",
        management_path="data.sample_event.management",
        sample_date_path="data.sample_event.sample_date",
        num_quadrats_path="data.quadrat_transect.num_quadrats",
    )


def test_different_num_quadrats_no_existing(valid_benthic_pq_transect_collect_record):
    validator = _get_num_quadrats_validator()
    record = CollectRecordSerializer(instance=valid_benthic_pq_transect_collect_record).data

    result = validator(record)
    assert result.status == OK


def test_different_num_quadrats_same_value(
    benthic_photo_quadrat_transect1,
    valid_benthic_pq_transect_collect_record,
):
    # benthic_photo_quadrat_transect1 has num_quadrats=2
    valid_benthic_pq_transect_collect_record.data["quadrat_transect"]["num_quadrats"] = 2
    valid_benthic_pq_transect_collect_record.save()

    validator = _get_num_quadrats_validator()
    record = CollectRecordSerializer(instance=valid_benthic_pq_transect_collect_record).data

    result = validator(record)
    assert result.status == OK


def test_different_num_quadrats_different_value(
    benthic_photo_quadrat_transect1,
    valid_benthic_pq_transect_collect_record,
):
    # benthic_photo_quadrat_transect1 has num_quadrats=2
    valid_benthic_pq_transect_collect_record.data["quadrat_transect"]["num_quadrats"] = 5
    valid_benthic_pq_transect_collect_record.save()

    validator = _get_num_quadrats_validator()
    record = CollectRecordSerializer(instance=valid_benthic_pq_transect_collect_record).data

    result = validator(record)
    assert result.status == WARN
    assert result.code == DifferentNumQuadratsValidator.DIFFERENT_NUM_QUADRATS
    assert "num_quadrats" in result.context
    assert result.context["num_quadrats"] == 5
    assert "other_num_quadrats" in result.context
    assert result.context["other_num_quadrats"] == 2


def test_different_num_quadrats_different_site(
    valid_benthic_pq_transect_collect_record,
    site2,
):
    """Test when another PQT sample unit is at a different site (should not trigger warning)."""
    valid_benthic_pq_transect_collect_record.data["quadrat_transect"]["num_quadrats"] = 5
    valid_benthic_pq_transect_collect_record.data["sample_event"]["site"] = str(site2.id)
    valid_benthic_pq_transect_collect_record.save()

    validator = _get_num_quadrats_validator()
    record = CollectRecordSerializer(instance=valid_benthic_pq_transect_collect_record).data

    result = validator(record)
    assert result.status == OK


def test_different_num_quadrats_different_date(
    valid_benthic_pq_transect_collect_record,
    sample_date1,
):
    """Test when another PQT sample unit is on a different date (should not trigger warning)."""
    different_date = sample_date1 + timedelta(days=60)

    valid_benthic_pq_transect_collect_record.data["quadrat_transect"]["num_quadrats"] = 5
    valid_benthic_pq_transect_collect_record.data["sample_event"][
        "sample_date"
    ] = f"{different_date:%Y-%m-%d}"
    valid_benthic_pq_transect_collect_record.save()

    validator = _get_num_quadrats_validator()
    record = CollectRecordSerializer(instance=valid_benthic_pq_transect_collect_record).data

    result = validator(record)
    assert result.status == OK


# ==================== DifferentNumPointsPerQuadratValidator tests ====================


def _get_num_points_per_quadrat_validator():
    return DifferentNumPointsPerQuadratValidator(
        site_path="data.sample_event.site",
        management_path="data.sample_event.management",
        sample_date_path="data.sample_event.sample_date",
        num_points_per_quadrat_path="data.quadrat_transect.num_points_per_quadrat",
    )


def test_different_num_points_per_quadrat_same_value(
    benthic_photo_quadrat_transect1,
    valid_benthic_pq_transect_collect_record,
):
    # benthic_photo_quadrat_transect1 has num_points_per_quadrat=100
    valid_benthic_pq_transect_collect_record.data["quadrat_transect"][
        "num_points_per_quadrat"
    ] = 100
    valid_benthic_pq_transect_collect_record.save()

    validator = _get_num_points_per_quadrat_validator()
    record = CollectRecordSerializer(instance=valid_benthic_pq_transect_collect_record).data

    result = validator(record)
    assert result.status == OK


def test_different_num_points_per_quadrat_different_value(
    benthic_photo_quadrat_transect1,
    valid_benthic_pq_transect_collect_record,
):
    # benthic_photo_quadrat_transect1 has num_points_per_quadrat=100
    valid_benthic_pq_transect_collect_record.data["quadrat_transect"]["num_points_per_quadrat"] = 50
    valid_benthic_pq_transect_collect_record.save()

    validator = _get_num_points_per_quadrat_validator()
    record = CollectRecordSerializer(instance=valid_benthic_pq_transect_collect_record).data

    result = validator(record)
    assert result.status == WARN
    assert result.code == DifferentNumPointsPerQuadratValidator.DIFFERENT_NUM_POINTS_PER_QUADRAT
    assert result.context["num_points_per_quadrat"] == 50
    assert result.context["other_num_points_per_quadrat"] == 100


# ==================== DifferentTransectWidthValidator tests ====================


def _get_transect_width_validator():
    return DifferentTransectWidthValidator(
        site_path="data.sample_event.site",
        management_path="data.sample_event.management",
        sample_date_path="data.sample_event.sample_date",
        width_path="data.fishbelt_transect.width",
    )


def test_different_transect_width_same_value(
    fishbelt_transect1,
    valid_collect_record,
    belt_transect_width_5m,
    sample_date1,
):
    # fishbelt_transect1 has width=5m
    valid_collect_record.data["fishbelt_transect"]["width"] = str(belt_transect_width_5m.pk)
    valid_collect_record.data["sample_event"]["sample_date"] = f"{sample_date1:%Y-%m-%d}"
    valid_collect_record.save()

    validator = _get_transect_width_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data

    result = validator(record)
    assert result.status == OK


def test_different_transect_width_different_value(
    fishbelt_transect1,
    valid_collect_record,
    belt_transect_width_10m,
    sample_date1,
):
    # fishbelt_transect1 has width=5m
    valid_collect_record.data["fishbelt_transect"]["width"] = str(belt_transect_width_10m.pk)
    valid_collect_record.data["sample_event"]["sample_date"] = f"{sample_date1:%Y-%m-%d}"
    valid_collect_record.save()

    validator = _get_transect_width_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data

    result = validator(record)
    assert result.status == WARN
    assert result.code == DifferentTransectWidthValidator.DIFFERENT_TRANSECT_WIDTH


# ==================== DifferentTransectLengthValidator tests ====================


def _get_transect_length_validator():
    return DifferentTransectLengthValidator(
        protocol_path="data.protocol",
        site_path="data.sample_event.site",
        management_path="data.sample_event.management",
        sample_date_path="data.sample_event.sample_date",
        len_surveyed_path="data.benthic_transect.len_surveyed",
    )


def test_different_transect_length_same_value(
    benthic_lit1,
    valid_benthic_lit_collect_record,
):
    # benthic_lit1 has len_surveyed=50
    valid_benthic_lit_collect_record.data["benthic_transect"]["len_surveyed"] = 50
    valid_benthic_lit_collect_record.save()

    validator = _get_transect_length_validator()
    record = CollectRecordSerializer(instance=valid_benthic_lit_collect_record).data

    result = validator(record)
    assert result.status == OK


def test_different_transect_length_different_value(
    benthic_lit1,
    valid_benthic_lit_collect_record,
):
    # benthic_lit1 has len_surveyed=50
    valid_benthic_lit_collect_record.data["benthic_transect"]["len_surveyed"] = 100
    valid_benthic_lit_collect_record.save()

    validator = _get_transect_length_validator()
    record = CollectRecordSerializer(instance=valid_benthic_lit_collect_record).data

    result = validator(record)
    assert result.status == WARN
    assert result.code == DifferentTransectLengthValidator.DIFFERENT_TRANSECT_LENGTH
    assert result.context["len_surveyed"] == 100
    assert result.context["other_len_surveyed"] == 50


# ==================== DifferentQuadratSizeValidator tests ====================


def _get_quadrat_size_validator():
    return DifferentQuadratSizeValidator(
        site_path="data.sample_event.site",
        management_path="data.sample_event.management",
        sample_date_path="data.sample_event.sample_date",
        quadrat_size_path="data.quadrat_collection.quadrat_size",
    )


def test_different_quadrat_size_same_value(
    bleaching_quadrat_collection1,
    valid_bleaching_qc_collect_record,
):
    # bleaching_quadrat_collection1 has quadrat_size=1.0
    valid_bleaching_qc_collect_record.data["quadrat_collection"]["quadrat_size"] = 1.0
    valid_bleaching_qc_collect_record.save()

    validator = _get_quadrat_size_validator()
    record = CollectRecordSerializer(instance=valid_bleaching_qc_collect_record).data

    result = validator(record)
    assert result.status == OK


def test_different_quadrat_size_different_value(
    bleaching_quadrat_collection1,
    valid_bleaching_qc_collect_record,
):
    # bleaching_quadrat_collection1 has quadrat_size=1.0
    valid_bleaching_qc_collect_record.data["quadrat_collection"]["quadrat_size"] = 2.0
    valid_bleaching_qc_collect_record.save()

    validator = _get_quadrat_size_validator()
    record = CollectRecordSerializer(instance=valid_bleaching_qc_collect_record).data

    result = validator(record)
    assert result.status == WARN
    assert result.code == DifferentQuadratSizeValidator.DIFFERENT_QUADRAT_SIZE
    assert result.context["quadrat_size"] == 2.0
    assert result.context["other_quadrat_size"] == 1.0
