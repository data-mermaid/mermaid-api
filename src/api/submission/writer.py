import logging
import uuid

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, F, UniqueConstraint
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, serializers
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueTogetherValidator

from api.models import (
    Annotation,
    BeltFish,
    BeltInvert,
    BenthicLIT,
    BenthicPhotoQuadratTransect,
    BenthicPIT,
    BenthicTransect,
    BleachingQuadratCollection,
    FishBeltTransect,
    HabitatComplexity,
    InvertBeltTransect,
    ObsBeltFish,
    ObsBeltInvert,
    ObsBenthicLIT,
    ObsBenthicPhotoQuadrat,
    ObsBenthicPIT,
    ObsColoniesBleached,
    Observer,
    ObsHabitatComplexity,
    ObsQuadratBenthicPercent,
    QuadratCollection,
    QuadratTransect,
    SampleEvent,
)
from api.resources.base import get_request_profile
from api.resources.benthic_transect import BenthicTransectSerializer
from api.resources.fish_belt_transect import FishBeltTransectSerializer
from api.resources.invert_belt_transect import InvertBeltTransectSerializer
from api.resources.observer import ObserverSerializer
from api.resources.quadrat_collection import QuadratCollectionSerializer
from api.resources.quadrat_transect import QuadratTransectSerializer
from api.resources.sample_event import SampleEventSerializer
from api.utils import combine_into
from ..resources.sampleunitmethods import clean_sample_event_models
from ..resources.sampleunitmethods.beltfishmethod import (
    BeltFishSerializer,
    ObsBeltFishSerializer,
)
from ..resources.sampleunitmethods.beltinvertmethod import (
    BeltInvertSerializer,
    ObsBeltInvertSerializer,
)
from ..resources.sampleunitmethods.benthiclitmethod import (
    BenthicLITSerializer,
    ObsBenthicLITSerializer,
)
from ..resources.sampleunitmethods.benthicphotoquadrattransectmethod import (
    BenthicPhotoQuadratTransectSerializer,
    ObsBenthicPhotoQuadratSerializer,
)
from ..resources.sampleunitmethods.benthicpitmethod import (
    BenthicPITSerializer,
    ObsBenthicPITSerializer,
)
from ..resources.sampleunitmethods.bleachingquadratcollectionmethod import (
    BleachingQuadratCollectionSerializer,
    ObsColoniesBleachedSerializer,
    ObsQuadratBenthicPercentSerializer,
)
from ..resources.sampleunitmethods.habitatcomplexitymethod import (
    HabitatComplexitySerializer,
    ObsHabitatComplexitySerializer,
)
from .parser import (
    get_benthic_transect_data,
    get_fishbelt_transect_data,
    get_invertbelt_transect_data,
    get_obs_benthic_photo_quadrat_data,
    get_obs_colonies_bleached_data,
    get_obs_quadrat_benthic_percent_data,
    get_obsbeltfish_data,
    get_obsbeltinvert_data,
    get_obsbenthiclit_data,
    get_obsbenthicpit_data,
    get_observers_data,
    get_obshabitatcomplexity_data,
    get_quadrat_collection_data,
    get_quadrat_transect_data,
    get_sample_event_data,
)

logger = logging.getLogger(__name__)


class PreloadedPrimaryKeyField(serializers.Field):
    """
    Stands in for a PrimaryKeyRelatedField. It checks the ID against a set
    loaded once per write, in place of one query per value, and returns the
    ID in place of the related instance.
    """

    def __init__(self, related_model, valid_ids, **kwargs):
        self.related_model = related_model
        self.valid_ids = valid_ids
        super().__init__(**kwargs)

    def run_validation(self, data=serializers.empty):
        # Same as RelatedField: treat an empty string as no value.
        if data == "":
            data = None
        return super().run_validation(data)

    def to_internal_value(self, data):
        try:
            if isinstance(data, bool):
                raise TypeError
            pk = self.related_model._meta.pk.to_python(data)
        except (TypeError, ValueError, DjangoValidationError):
            self.fail("incorrect_type", data_type=type(data).__name__)

        if pk not in self.valid_ids:
            self.fail("does_not_exist", pk_value=data)
        return pk


class BaseWriter:
    def __init__(self, collect_record, context):
        self.collect_record = collect_record
        self.context = context

    def validate_data(self, serializer_cls, data):
        serializer = serializer_cls(data=data, context=self.context)
        if serializer.is_valid() is False:
            raise ValidationError(serializer.errors)

        return serializer

    def get_or_create(self, model, serializer_cls, data, additional_data=None):
        pk = data.get("id") or uuid.uuid4()
        data["id"] = pk
        serializer = self.validate_data(serializer_cls, data)

        try:
            data.pop("id")
            return model.objects.get(**data)
        except model.DoesNotExist:
            if isinstance(additional_data, dict):
                data["id"] = pk
                combine_into(additional_data, data)
                serializer = self.validate_data(serializer_cls, data)
            return serializer.save()

    def _preload_related_ids(self, serializer_cls, records_data):
        """
        For each writable PrimaryKeyRelatedField of `serializer_cls`, load the
        IDs in `records_data` that exist, with one query per field.
        """
        preloaded = {}
        fields = serializer_cls(context=self.context).fields
        for name, field in fields.items():
            if not isinstance(field, serializers.PrimaryKeyRelatedField) or field.read_only:
                continue

            queryset = field.get_queryset()
            pk_field = queryset.model._meta.pk
            ids = set()
            for record_data in records_data:
                value = record_data.get(name)
                if value in (None, "") or isinstance(value, bool):
                    continue
                try:
                    ids.add(pk_field.to_python(value))
                except (TypeError, ValueError, DjangoValidationError):
                    # The field reports the bad value during validation.
                    continue

            valid_ids = set()
            if ids:
                valid_ids = set(queryset.filter(pk__in=ids).values_list("pk", flat=True))
            preloaded[name] = (field, valid_ids)

        return preloaded

    def bulk_create_records(self, model, serializer_cls, records_data):
        """
        Validate each record with `serializer_cls` and insert all of them with
        one bulk_create.

        Related IDs are checked against sets loaded once. The serializer's
        unique-together validators are skipped: they run one query per record,
        and the database constraints still apply.

        bulk_create does not send save signals. This sets created_by and
        updated_by in place of the `set_created_by` pre_save signal. The
        `update_project_updated_on` post_save signal is not needed: the sample
        unit method and observers saved by the same write touch the project.
        """
        preloaded = self._preload_related_ids(serializer_cls, records_data)
        profile = self._get_profile()

        instances = []
        for record_data in records_data:
            record_data["id"] = record_data.get("id") or uuid.uuid4()
            serializer = serializer_cls(data=record_data, context=self.context)
            for name, (field, valid_ids) in preloaded.items():
                serializer.fields[name] = PreloadedPrimaryKeyField(
                    related_model=field.get_queryset().model,
                    valid_ids=valid_ids,
                    source=model._meta.get_field(field.source).attname,
                    required=field.required,
                    allow_null=field.allow_null,
                    error_messages=field.error_messages,
                )
            serializer.validators = []
            if serializer.is_valid() is False:
                raise ValidationError(serializer.errors)

            instances.append(
                model(**serializer.validated_data, created_by=profile, updated_by=profile)
            )

        try:
            with transaction.atomic():
                return model.objects.bulk_create(instances)
        except IntegrityError as err:
            logger.warning("bulk_create_records: %s", err)
            raise ValidationError(
                {"non_field_errors": [self._integrity_error_message(model, serializer_cls, err)]}
            ) from err

    def _get_profile(self):
        # Same as CurrentProfileDefault.
        request = self.context.get("request")
        if request is None:
            return None
        try:
            return get_request_profile(request)
        except exceptions.AuthenticationFailed:
            return None

    def _integrity_error_message(self, model, serializer_cls, err):
        """
        A user-facing message for `err`. The raw database message contains
        constraint names and values, so it is not returned to the client.
        """
        constraint_name = getattr(getattr(err.__cause__, "diag", None), "constraint_name", None)
        for constraint in model._meta.constraints:
            if isinstance(constraint, UniqueConstraint) and constraint.name == constraint_name:
                # Same message as the skipped UniqueTogetherValidator, whether
                # declared on the serializer or generated from the model.
                for validator in serializer_cls(context=self.context).validators:
                    if isinstance(validator, UniqueTogetherValidator) and set(
                        validator.fields
                    ) == set(constraint.fields):
                        return str(validator.message)
                field_names = ", ".join(constraint.fields)
                return str(_("The fields {} must make a unique set.").format(field_names))
        return str(_("The records could not be saved because they conflict with existing data."))

    def write(self):
        raise NotImplementedError()


class ProtocolWriter(BaseWriter):
    def get_sample_unit_method_id(self):
        return self.collect_record.data.get("sample_unit_method_id")

    def get_or_create_sample_event(self):
        sample_event_data = get_sample_event_data(self.collect_record)
        clean_sample_event_models(sample_event_data)
        return self.get_or_create(SampleEvent, SampleEventSerializer, sample_event_data)

    def create_observers(self, sample_unit_method_id):
        observers = []
        observers_data = get_observers_data(self.collect_record, sample_unit_method_id)
        if not observers_data:
            raise ValidationError({"observers": [str(_("Must have at least 1 observer."))]})

        for observer_data in observers_data:
            observer_data["id"] = uuid.uuid4()
            serializer = self.validate_data(ObserverSerializer, observer_data)
            try:
                observer_data.pop("id")
                observers.append(Observer.objects.get(**observer_data))
            except Observer.DoesNotExist:
                if serializer.is_valid() is False:
                    raise ValidationError(serializer.errors) from _
                observers.append(serializer.save())

        return observers


class BenthicProtocolWriter(ProtocolWriter):
    def get_or_create_benthic_transect(self, sample_event_id):
        benthic_transect_data = get_benthic_transect_data(self.collect_record, sample_event_id)
        return self.get_or_create(BenthicTransect, BenthicTransectSerializer, benthic_transect_data)


class FishbeltProtocolWriter(ProtocolWriter):
    def get_or_create_fishbelt_transect(self, sample_event_id):
        fishbelt_transect_data = get_fishbelt_transect_data(self.collect_record, sample_event_id)
        return self.get_or_create(
            FishBeltTransect, FishBeltTransectSerializer, fishbelt_transect_data
        )

    def get_or_create_beltfish(
        self, collect_record_id, fishbelt_transect_id, sample_unit_method_id=None
    ):
        beltfish_data = {"transect": fishbelt_transect_id, "id": sample_unit_method_id}
        return self.get_or_create(
            BeltFish,
            BeltFishSerializer,
            beltfish_data,
            additional_data={"collect_record_id": collect_record_id},
        )

    def create_obsbeltfish(self, belt_fish_id):
        observations_data = get_obsbeltfish_data(self.collect_record, belt_fish_id)
        return self.bulk_create_records(ObsBeltFish, ObsBeltFishSerializer, observations_data)

    def write(self):
        sample_unit_method_id = self.get_sample_unit_method_id()
        sample_event = self.get_or_create_sample_event()
        fishbelt_transect = self.get_or_create_fishbelt_transect(sample_event.id)
        belt_fish = self.get_or_create_beltfish(
            self.collect_record.id, fishbelt_transect.id, sample_unit_method_id
        )
        _ = self.create_observers(belt_fish.id)
        _ = self.create_obsbeltfish(belt_fish.id)


class BenthicPITProtocolWriter(BenthicProtocolWriter):
    def get_or_create_benthicpit(
        self, collect_record_id, benthic_transect_id, sample_unit_method_id=None
    ):
        benthic_pit_data = {
            "id": sample_unit_method_id,
            "transect": benthic_transect_id,
            "interval_size": self.collect_record.data.get("interval_size"),
            "interval_start": self.collect_record.data.get("interval_start"),
        }
        return self.get_or_create(
            BenthicPIT,
            BenthicPITSerializer,
            benthic_pit_data,
            additional_data={"collect_record_id": collect_record_id},
        )

    def create_obsbenthicpit(self, benthic_pit_id):
        observations_data = get_obsbenthicpit_data(self.collect_record, benthic_pit_id)
        if not observations_data:
            raise ValidationError(
                {"obs_benthic_pits": [_("Benthic PIT observations are required.")]}
            )

        return self.bulk_create_records(ObsBenthicPIT, ObsBenthicPITSerializer, observations_data)

    def write(self):
        sample_unit_method_id = self.get_sample_unit_method_id()
        sample_event = self.get_or_create_sample_event()
        benthic_transect = self.get_or_create_benthic_transect(sample_event.id)
        benthic_pit = self.get_or_create_benthicpit(
            self.collect_record.id, benthic_transect.id, sample_unit_method_id
        )
        _ = self.create_observers(benthic_pit.id)
        _ = self.create_obsbenthicpit(benthic_pit.id)


class BenthicLITProtocolWriter(BenthicProtocolWriter):
    def get_or_create_benthiclit(
        self, collect_record_id, benthic_transect_id, sample_unit_method_id=None
    ):
        benthic_lit_data = {
            "transect": benthic_transect_id,
            "id": sample_unit_method_id,
        }
        return self.get_or_create(
            BenthicLIT,
            BenthicLITSerializer,
            benthic_lit_data,
            additional_data={"collect_record_id": collect_record_id},
        )

    def create_obsbenthiclit(self, benthic_lit_id):
        observations_data = get_obsbenthiclit_data(self.collect_record, benthic_lit_id)
        if not observations_data:
            raise ValidationError(
                {"obs_benthic_lits": [_("Benthic LIT observations are required.")]}
            )

        return self.bulk_create_records(ObsBenthicLIT, ObsBenthicLITSerializer, observations_data)

    def write(self):
        sample_unit_method_id = self.get_sample_unit_method_id()
        sample_event = self.get_or_create_sample_event()
        benthic_transect = self.get_or_create_benthic_transect(sample_event.id)
        benthic_lit = self.get_or_create_benthiclit(
            self.collect_record.id, benthic_transect.id, sample_unit_method_id
        )
        _ = self.create_observers(benthic_lit.id)
        _ = self.create_obsbenthiclit(benthic_lit.id)


class HabitatComplexityProtocolWriter(BenthicProtocolWriter):
    def get_or_create_habitatcomplexity(
        self, collect_record_id, benthic_transect_id, sample_unit_method_id=None
    ):
        habitat_complexity_data = {
            "id": sample_unit_method_id,
            "transect": benthic_transect_id,
            "interval_size": self.collect_record.data.get("interval_size"),
            "interval_start": self.collect_record.data.get("interval_start"),
        }
        return self.get_or_create(
            HabitatComplexity,
            HabitatComplexitySerializer,
            habitat_complexity_data,
            additional_data={"collect_record_id": collect_record_id},
        )

    def create_obshabitatcomplexity(self, habitatcomplexity_id):
        observations_data = get_obshabitatcomplexity_data(self.collect_record, habitatcomplexity_id)
        if not observations_data:
            raise ValidationError(
                {"obs_habitat_complexities": [_("Habitat complexity observations are required.")]}
            )

        return self.bulk_create_records(
            ObsHabitatComplexity, ObsHabitatComplexitySerializer, observations_data
        )

    def write(self):
        sample_unit_method_id = self.get_sample_unit_method_id()
        sample_event = self.get_or_create_sample_event()
        benthic_transect = self.get_or_create_benthic_transect(sample_event.id)
        habitat_complexity = self.get_or_create_habitatcomplexity(
            self.collect_record.id, benthic_transect.id, sample_unit_method_id
        )
        _ = self.create_observers(habitat_complexity.id)
        _ = self.create_obshabitatcomplexity(habitat_complexity.id)


class BleachingQuadratCollectionProtocolWriter(ProtocolWriter):
    def get_or_create_quadrat_collection(self, sample_event_id):
        observation_data = get_quadrat_collection_data(self.collect_record, sample_event_id)
        try:
            return QuadratCollection.objects.get(**observation_data)

        except (QuadratCollection.DoesNotExist, ValidationError):
            observation_data["id"] = observation_data.get("id") or uuid.uuid4()
            serializer = QuadratCollectionSerializer(data=observation_data, context=self.context)
            if serializer.is_valid() is False:
                raise ValidationError(serializer.errors) from _

            return serializer.save()

    def get_or_create_bleaching_quadrat_collection(
        self, collect_record_id, quadrat_collection_id, sample_unit_method_id=None
    ):
        bleaching_quadrat_collection_data = {
            "quadrat": quadrat_collection_id,
            "id": sample_unit_method_id,
        }
        return self.get_or_create(
            BleachingQuadratCollection,
            BleachingQuadratCollectionSerializer,
            bleaching_quadrat_collection_data,
            additional_data={"collect_record_id": collect_record_id},
        )

    def create_obs_quadrat_benthic_percent(self, bleaching_quadrat_collection_id):
        observations_data = get_obs_quadrat_benthic_percent_data(
            self.collect_record, bleaching_quadrat_collection_id
        )
        if not observations_data:
            return []

        return self.bulk_create_records(
            ObsQuadratBenthicPercent, ObsQuadratBenthicPercentSerializer, observations_data
        )

    def create_obs_colonies_bleached(self, bleaching_quadrat_collection_id):
        observations_data = get_obs_colonies_bleached_data(
            self.collect_record, bleaching_quadrat_collection_id
        )
        if not observations_data:
            raise ValidationError(
                {"obs_colonies_bleached": [_("Colonies bleached observations are required.")]}
            )

        return self.bulk_create_records(
            ObsColoniesBleached, ObsColoniesBleachedSerializer, observations_data
        )

    def write(self):
        sample_unit_method_id = self.get_sample_unit_method_id()
        sample_event = self.get_or_create_sample_event()
        quadrat_collection = self.get_or_create_quadrat_collection(sample_event.id)
        bleaching_quadrat_collection = self.get_or_create_bleaching_quadrat_collection(
            self.collect_record.id, quadrat_collection.id, sample_unit_method_id
        )
        _ = self.create_observers(bleaching_quadrat_collection.id)
        _ = self.create_obs_quadrat_benthic_percent(bleaching_quadrat_collection.id)
        _ = self.create_obs_colonies_bleached(bleaching_quadrat_collection.id)


class BenthicPhotoQuadratTransectProtocolWriter(ProtocolWriter):
    def get_or_create_quadrat_transect(self, sample_event_id):
        quadrat_transect_data = get_quadrat_transect_data(self.collect_record, sample_event_id)
        try:
            return QuadratTransect.objects.get(**quadrat_transect_data)

        except (QuadratTransect.DoesNotExist, ValidationError) as _:
            quadrat_transect_data["id"] = uuid.uuid4()
            serializer = QuadratTransectSerializer(data=quadrat_transect_data, context=self.context)
            if serializer.is_valid() is False:
                raise ValidationError(serializer.errors) from _

            return serializer.save()

    def get_or_create_benthic_photo_quadrat_transect(
        self, collect_record_id, quadrat_transect_id, sample_unit_method_id=None
    ):
        benthic_photo_quadrat_transect_data = {
            "quadrat_transect": quadrat_transect_id,
            "id": sample_unit_method_id,
        }
        image_classification = self.collect_record.data.get("image_classification") or False
        additional_data = {
            "collect_record_id": collect_record_id,
            "image_classification": image_classification,
        }
        return self.get_or_create(
            BenthicPhotoQuadratTransect,
            BenthicPhotoQuadratTransectSerializer,
            benthic_photo_quadrat_transect_data,
            additional_data=additional_data,
        )

    def _group_image_annotations(self, collect_record_id):
        return (
            Annotation.objects.filter(
                is_confirmed=True, point__image__collect_record_id=collect_record_id
            )
            .values(
                image_id=F("point__image_id"),
                attribute_id=F("benthic_attribute_id"),
                _growth_form_id=F("growth_form_id"),
            )
            .annotate(count=Count("id"))
            .order_by("point__image__created_on")
        )

    def get_and_format_annotations(self, benthic_photo_quadrat_transect_id):
        collect_record_id = self.collect_record.id
        observations_data = []
        annos = self._group_image_annotations(collect_record_id)

        quadrat_num_start = (self.collect_record.data.get("quadrat_transect") or {}).get(
            "quadrat_number_start"
        ) or 1

        seen_images = []
        quadrat_num = quadrat_num_start - 1
        for anno in annos:
            image_id = anno.get("image_id")
            attribute_id = anno.get("attribute_id")
            growth_form_id = anno.get("_growth_form_id")
            count = anno.get("count") or 0

            if not image_id or not attribute_id:
                continue
            if image_id not in seen_images:
                seen_images.append(image_id)
                quadrat_num += 1

            observations_data.append(
                {
                    "benthic_photo_quadrat_transect": benthic_photo_quadrat_transect_id,
                    "image": image_id,
                    "attribute": attribute_id,
                    "growth_form": growth_form_id,
                    "quadrat_number": quadrat_num,
                    "num_points": count,
                }
            )

        return observations_data

    def create_obs_benthic_photo_quadrat(self, benthic_photo_quadrat_transect_id):
        image_classification = self.collect_record.data.get("image_classification")

        if image_classification:
            observations_data = self.get_and_format_annotations(benthic_photo_quadrat_transect_id)
        else:
            observations_data = get_obs_benthic_photo_quadrat_data(
                self.collect_record, benthic_photo_quadrat_transect_id
            )

        if not observations_data:
            raise ValidationError(
                {
                    "obs_benthic_photo_quadrats": [
                        _("Benthic Photo Quadrat observations are required.")
                    ]
                }
            )

        return self.bulk_create_records(
            ObsBenthicPhotoQuadrat, ObsBenthicPhotoQuadratSerializer, observations_data
        )

    def write(self):
        sample_unit_method_id = self.get_sample_unit_method_id()
        sample_event = self.get_or_create_sample_event()
        quadrat_transect = self.get_or_create_quadrat_transect(sample_event.id)
        benthic_photo_quadrat_transect = self.get_or_create_benthic_photo_quadrat_transect(
            self.collect_record.id, quadrat_transect.id, sample_unit_method_id
        )
        _ = self.create_observers(benthic_photo_quadrat_transect.id)
        _ = self.create_obs_benthic_photo_quadrat(benthic_photo_quadrat_transect.id)


class BeltInvertProtocolWriter(ProtocolWriter):
    def get_or_create_invertbelt_transect(self, sample_event_id):
        invertbelt_transect_data = get_invertbelt_transect_data(
            self.collect_record, sample_event_id
        )
        return self.get_or_create(
            InvertBeltTransect, InvertBeltTransectSerializer, invertbelt_transect_data
        )

    def get_or_create_beltinvert(
        self, collect_record_id, invertbelt_transect_id, sample_unit_method_id=None
    ):
        beltinvert_data = {"transect": invertbelt_transect_id, "id": sample_unit_method_id}
        return self.get_or_create(
            BeltInvert,
            BeltInvertSerializer,
            beltinvert_data,
            additional_data={"collect_record_id": collect_record_id},
        )

    def create_obsbeltinvert(self, belt_invert_id):
        observations_data = get_obsbeltinvert_data(self.collect_record, belt_invert_id)
        return self.bulk_create_records(ObsBeltInvert, ObsBeltInvertSerializer, observations_data)

    def write(self):
        sample_unit_method_id = self.get_sample_unit_method_id()
        sample_event = self.get_or_create_sample_event()
        invertbelt_transect = self.get_or_create_invertbelt_transect(sample_event.id)
        belt_invert = self.get_or_create_beltinvert(
            self.collect_record.id, invertbelt_transect.id, sample_unit_method_id
        )
        _ = self.create_observers(belt_invert.id)
        _ = self.create_obsbeltinvert(belt_invert.id)
