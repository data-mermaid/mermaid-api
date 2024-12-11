import uuid

from django.db.models import Count, F
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from api.models import (
    Annotation,
    BeltFish,
    BenthicLIT,
    BenthicPhotoQuadratTransect,
    BenthicPIT,
    BenthicTransect,
    BleachingQuadratCollection,
    FishBeltTransect,
    HabitatComplexity,
    Observer,
    QuadratCollection,
    QuadratTransect,
    SampleEvent,
)
from api.resources.benthic_transect import BenthicTransectSerializer
from api.resources.fish_belt_transect import FishBeltTransectSerializer
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
    get_obs_benthic_photo_quadrat_data,
    get_obs_colonies_bleached_data,
    get_obs_quadrat_benthic_percent_data,
    get_obsbeltfish_data,
    get_obsbenthiclit_data,
    get_obsbenthicpit_data,
    get_observers_data,
    get_obshabitatcomplexity_data,
    get_quadrat_collection_data,
    get_quadrat_transect_data,
    get_sample_event_data,
)


class BaseWriter(object):
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
        observation_beltfishes = []
        observations_data = get_obsbeltfish_data(self.collect_record, belt_fish_id)

        for observation_data in observations_data:
            observation_data["id"] = observation_data.get("id") or uuid.uuid4()
            serializer = self.validate_data(ObsBeltFishSerializer, observation_data)
            observation_beltfishes.append(serializer.save())

        return observation_beltfishes

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
        observation_benthicpits = []
        observations_data = get_obsbenthicpit_data(self.collect_record, benthic_pit_id)
        if not observations_data:
            raise ValidationError(
                {"obs_benthic_pits": [_("Benthic PIT observations are required.")]}
            )

        for observation_data in observations_data:
            observation_data["id"] = observation_data.get("id") or uuid.uuid4()
            serializer = ObsBenthicPITSerializer(data=observation_data, context=self.context)
            if serializer.is_valid() is False:
                raise ValidationError(serializer.errors)

            observation_benthicpits.append(serializer.save())

        return observation_benthicpits

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
        observation_benthiclits = []
        observations_data = get_obsbenthiclit_data(self.collect_record, benthic_lit_id)
        if not observations_data:
            raise ValidationError(
                {"obs_benthic_lits": [_("Benthic LIT observations are required.")]}
            )

        for observation_data in observations_data:
            observation_data["id"] = observation_data.get("id") or uuid.uuid4()
            serializer = ObsBenthicLITSerializer(data=observation_data, context=self.context)
            if serializer.is_valid() is False:
                raise ValidationError(serializer.errors)

            observation_benthiclits.append(serializer.save())

        return observation_benthiclits

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
        }
        return self.get_or_create(
            HabitatComplexity,
            HabitatComplexitySerializer,
            habitat_complexity_data,
            additional_data={"collect_record_id": collect_record_id},
        )

    def create_obshabitatcomplexity(self, habitatcomplexity_id):
        observation_habitatcomplexities = []
        observations_data = get_obshabitatcomplexity_data(self.collect_record, habitatcomplexity_id)
        if not observations_data:
            raise ValidationError(
                {"obs_habitat_complexities": [_("Habitat complexity observations are required.")]}
            )

        for observation_data in observations_data:
            observation_data["id"] = observation_data.get("id") or uuid.uuid4()
            serializer = ObsHabitatComplexitySerializer(data=observation_data, context=self.context)
            if serializer.is_valid() is False:
                raise ValidationError(serializer.errors)

            observation_habitatcomplexities.append(serializer.save())

        return observation_habitatcomplexities

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
        observation_benthic_percent_covered_data = []
        observations_data = get_obs_quadrat_benthic_percent_data(
            self.collect_record, bleaching_quadrat_collection_id
        )
        if not observations_data:
            return observation_benthic_percent_covered_data

        for observation_data in observations_data:
            observation_data["id"] = observation_data.get("id") or uuid.uuid4()
            serializer = ObsQuadratBenthicPercentSerializer(
                data=observation_data, context=self.context
            )
            if serializer.is_valid() is False:
                raise ValidationError(serializer.errors)

            observation_benthic_percent_covered_data.append(serializer.save())

        return observation_benthic_percent_covered_data

    def create_obs_colonies_bleached(self, bleaching_quadrat_collection_id):
        observation_benthic_percent_covered_data = []
        observations_data = get_obs_colonies_bleached_data(
            self.collect_record, bleaching_quadrat_collection_id
        )
        if not observations_data:
            raise ValidationError(
                {"obs_colonies_bleached": [_("Colonies bleached observations are required.")]}
            )

        for observation_data in observations_data:
            observation_data["id"] = observation_data.get("id") or uuid.uuid4()
            serializer = ObsColoniesBleachedSerializer(data=observation_data, context=self.context)
            if serializer.is_valid() is False:
                raise ValidationError(serializer.errors)

            observation_benthic_percent_covered_data.append(serializer.save())

        return observation_benthic_percent_covered_data

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

        images = {}
        quadrat_num = quadrat_num_start
        for anno in annos:
            image_id = anno.get("image_id")
            attribute_id = anno.get("attribute_id")
            growth_form_id = anno.get("_growth_form_id")
            count = anno.get("count") or 0

            if not image_id or not attribute_id:
                continue

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
            if image_id not in images:
                quadrat_num += 1
                images[image_id] = None

        return observations_data

    def create_obs_benthic_photo_quadrat(self, benthic_photo_quadrat_transect_id):
        observations = []
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

        for observation_data in observations_data:
            observation_data["id"] = observation_data.get("id") or uuid.uuid4()
            serializer = ObsBenthicPhotoQuadratSerializer(
                data=observation_data, context=self.context
            )
            if serializer.is_valid() is False:
                raise ValidationError(serializer.errors)

            observations.append(serializer.save())

        return observations

    def write(self):
        sample_unit_method_id = self.get_sample_unit_method_id()
        sample_event = self.get_or_create_sample_event()
        quadrat_transect = self.get_or_create_quadrat_transect(sample_event.id)
        benthic_photo_quadrat_transect = self.get_or_create_benthic_photo_quadrat_transect(
            self.collect_record.id, quadrat_transect.id, sample_unit_method_id
        )
        _ = self.create_observers(benthic_photo_quadrat_transect.id)
        _ = self.create_obs_benthic_photo_quadrat(benthic_photo_quadrat_transect.id)
