import uuid

from django.utils.translation import ugettext_lazy as _
from rest_framework.exceptions import ValidationError

from api.models import (
    BeltFish,
    BenthicLIT,
    BenthicPIT,
    BenthicTransect,
    BleachingQuadratCollection,
    FishBeltTransect,
    HabitatComplexity,
    Observer,
    QuadratCollection,
    SampleEvent,
)
from api.resources.belt_fish import BeltFishSerializer
from api.resources.benthic_lit import BenthicLITSerializer
from api.resources.benthic_pit import BenthicPITSerializer
from api.resources.benthic_transect import BenthicTransectSerializer
from api.resources.bleaching_quadrat_collection import (
    BleachingQuadratCollectionSerializer,
)
from api.resources.fish_belt_transect import FishBeltTransectSerializer
from api.resources.habitat_complexity import HabitatComplexitySerializer
from api.resources.obs_belt_fish import ObsBeltFishSerializer
from api.resources.obs_benthic_lit import ObsBenthicLITSerializer
from api.resources.obs_benthic_pit import ObsBenthicPITSerializer
from api.resources.obs_colonies_bleached import ObsColoniesBleachedSerializer
from api.resources.obs_habitat_complexity import ObsHabitatComplexitySerializer
from api.resources.obs_quadrat_benthic_percent import ObsQuadratBenthicPercentSerializer
from api.resources.observer import ObserverSerializer
from api.resources.quadrat_collection import QuadratCollectionSerializer
from api.resources.sample_event import SampleEventSerializer
from .parser import (
    get_benthic_transect_data,
    get_fishbelt_transect_data,
    get_obs_colonies_bleached_data,
    get_obs_quadrat_benthic_percent_data,
    get_obsbeltfish_data,
    get_obsbenthiclit_data,
    get_obsbenthicpit_data,
    get_observers_data,
    get_obshabitatcomplexity_data,
    get_quadrat_collection_data,
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

    def get_or_create(self, model, serializer_cls, data):
        data["id"] = data.get("id") or uuid.uuid4()
        serializer = self.validate_data(serializer_cls, data)
        try:
            data.pop("id")
            return model.objects.get(**data)
        except model.DoesNotExist:
            return serializer.save()

    def write(self):
        raise NotImplementedError()


class ProtocolWriter(BaseWriter):
    def get_sample_unit_method_id(self):
        return self.collect_record.data.get("sample_unit_method_id")

    def get_or_create_sample_event(self):
        sample_event_data = get_sample_event_data(self.collect_record)
        sample_event_data["id"] = uuid.uuid4()
        serializer = self.validate_data(SampleEventSerializer, sample_event_data)
        query_params = {
            k: v for k, v in sample_event_data.items() if k not in ("id", "notes")
        }
        se = SampleEvent.objects.filter(**query_params)
        if se.exists():
            sample_event = se[0]
            notes = sample_event_data.get("notes") or ""
            if notes.strip():
                sample_event.notes += "\n\n{}".format(notes)
                sample_event.save()
            return sample_event
        return serializer.save()

    def create_observers(self, sample_unit_method_id):
        observers = []
        observers_data = get_observers_data(self.collect_record, sample_unit_method_id)
        if not observers_data:
            raise ValidationError(
                {"observers": [str(_(u"Must have at least 1 observer."))]}
            )

        for observer_data in observers_data:
            observer_data["id"] = uuid.uuid4()
            serializer = self.validate_data(ObserverSerializer, observer_data)
            try:
                observer_data.pop("id")
                observers.append(Observer.objects.get(**observer_data))
            except Observer.DoesNotExist:
                if serializer.is_valid() is False:
                    raise ValidationError(serializer.errors)
                observers.append(serializer.save())

        return observers


class BenthicProtocolWriter(ProtocolWriter):
    def get_or_create_benthic_transect(self, sample_event_id):
        benthic_transect_data = get_benthic_transect_data(
            self.collect_record, sample_event_id
        )
        try:
            return BenthicTransect.objects.get(**benthic_transect_data)

        except (BenthicTransect.DoesNotExist, ValidationError):
            benthic_transect_data["id"] = uuid.uuid4()
            serializer = BenthicTransectSerializer(
                data=benthic_transect_data, context=self.context
            )
            if serializer.is_valid() is False:
                raise ValidationError(serializer.errors)

            return serializer.save()


class FishbeltProtocolWriter(ProtocolWriter):
    def get_or_create_fishbelt_transect(self, sample_event_id):
        fishbelt_transect_data = get_fishbelt_transect_data(
            self.collect_record, sample_event_id
        )
        return self.get_or_create(
            FishBeltTransect, FishBeltTransectSerializer, fishbelt_transect_data
        )

    def get_or_create_beltfish(self, fishbelt_transect_id, sample_unit_method_id=None):
        beltfish_data = {"transect": fishbelt_transect_id, "id": sample_unit_method_id}
        return self.get_or_create(BeltFish, BeltFishSerializer, beltfish_data)

    def create_obsbeltfish(self, belt_fish_id):
        observation_beltfishes = []
        observations_data = get_obsbeltfish_data(self.collect_record, belt_fish_id)

        for observation_data in observations_data:
            observation_data["id"] = uuid.uuid4()
            serializer = self.validate_data(ObsBeltFishSerializer, observation_data)
            observation_beltfishes.append(serializer.save())

        return observation_beltfishes

    def write(self):
        sample_unit_method_id = self.get_sample_unit_method_id()
        sample_event = self.get_or_create_sample_event()
        fishbelt_transect = self.get_or_create_fishbelt_transect(sample_event.id)
        belt_fish = self.get_or_create_beltfish(fishbelt_transect.id, sample_unit_method_id)
        _ = self.create_observers(belt_fish.id)
        _ = self.create_obsbeltfish(belt_fish.id)


class BenthicPITProtocolWriter(BenthicProtocolWriter):
    def get_or_create_benthicpit(self, benthic_transect_id, sample_unit_method_id=None):
        benthic_pit_data = {
            "id": sample_unit_method_id,
            "transect": benthic_transect_id,
            "interval_size": self.collect_record.data.get("interval_size"),
            "interval_start": self.collect_record.data.get("interval_start"),
        }
        return self.get_or_create(BenthicPIT, BenthicPITSerializer, benthic_pit_data)

    def create_obsbenthicpit(self, benthic_pit_id):
        observation_benthicpits = []
        observations_data = get_obsbenthicpit_data(self.collect_record, benthic_pit_id)
        if not observations_data:
            raise ValidationError(
                {"obs_benthic_pits": [_(u"Benthic PIT observations are required.")]}
            )

        for observation_data in observations_data:
            observation_data["id"] = uuid.uuid4()
            serializer = ObsBenthicPITSerializer(
                data=observation_data, context=self.context
            )
            if serializer.is_valid() is False:
                raise ValidationError(serializer.errors)

            observation_benthicpits.append(serializer.save())

        return observation_benthicpits

    def write(self):
        sample_unit_method_id = self.get_sample_unit_method_id()
        sample_event = self.get_or_create_sample_event()
        benthic_transect = self.get_or_create_benthic_transect(sample_event.id)
        benthic_pit = self.get_or_create_benthicpit(benthic_transect.id, sample_unit_method_id)
        _ = self.create_observers(benthic_pit.id)
        _ = self.create_obsbenthicpit(benthic_pit.id)


class BenthicLITProtocolWriter(BenthicProtocolWriter):
    def get_or_create_benthiclit(self, benthic_transect_id, sample_unit_method_id=None):
        benthic_lit_data = {"transect": benthic_transect_id, "id": sample_unit_method_id}
        return self.get_or_create(BenthicLIT, BenthicLITSerializer, benthic_lit_data)

    def create_obsbenthiclit(self, benthic_lit_id):
        observation_benthiclits = []
        observations_data = get_obsbenthiclit_data(self.collect_record, benthic_lit_id)
        if not observations_data:
            raise ValidationError(
                {"obs_benthic_lits": [_(u"Benthic LIT observations are required.")]}
            )

        for observation_data in observations_data:
            observation_data["id"] = uuid.uuid4()
            serializer = ObsBenthicLITSerializer(
                data=observation_data, context=self.context
            )
            if serializer.is_valid() is False:
                raise ValidationError(serializer.errors)

            observation_benthiclits.append(serializer.save())

        return observation_benthiclits

    def write(self):
        sample_unit_method_id = self.get_sample_unit_method_id()
        sample_event = self.get_or_create_sample_event()
        benthic_transect = self.get_or_create_benthic_transect(sample_event.id)
        benthic_lit = self.get_or_create_benthiclit(benthic_transect.id, sample_unit_method_id)
        _ = self.create_observers(benthic_lit.id)
        _ = self.create_obsbenthiclit(benthic_lit.id)


class HabitatComplexityProtocolWriter(BenthicProtocolWriter):
    def get_or_create_habitatcomplexity(self, benthic_transect_id, sample_unit_method_id=None):
        habitat_complexity_data = {
            "id": sample_unit_method_id,
            "transect": benthic_transect_id,
            "interval_size": self.collect_record.data.get("interval_size"),
        }
        return self.get_or_create(
            HabitatComplexity, HabitatComplexitySerializer, habitat_complexity_data
        )

    def create_obshabitatcomplexity(self, habitatcomplexity_id):
        observation_habitatcomplexities = []
        observations_data = get_obshabitatcomplexity_data(
            self.collect_record, habitatcomplexity_id
        )
        if not observations_data:
            raise ValidationError(
                {
                    "obs_habitat_complexities": [
                        _(u"Habitat complexity observations are required.")
                    ]
                }
            )

        for observation_data in observations_data:
            observation_data["id"] = uuid.uuid4()
            serializer = ObsHabitatComplexitySerializer(
                data=observation_data, context=self.context
            )
            if serializer.is_valid() is False:
                raise ValidationError(serializer.errors)

            observation_habitatcomplexities.append(serializer.save())

        return observation_habitatcomplexities

    def write(self):
        sample_unit_method_id = self.get_sample_unit_method_id()
        sample_event = self.get_or_create_sample_event()
        benthic_transect = self.get_or_create_benthic_transect(sample_event.id)
        habitat_complexity = self.get_or_create_habitatcomplexity(benthic_transect.id, sample_unit_method_id)
        _ = self.create_observers(habitat_complexity.id)
        _ = self.create_obshabitatcomplexity(habitat_complexity.id)


class BleachingQuadratCollectionProtocolWriter(ProtocolWriter):
    def get_or_create_quadrat_collection(self, sample_event_id):
        quadrat_collection_data = get_quadrat_collection_data(
            self.collect_record, sample_event_id
        )
        try:
            return QuadratCollection.objects.get(**quadrat_collection_data)

        except (QuadratCollection.DoesNotExist, ValidationError):
            quadrat_collection_data["id"] = uuid.uuid4()
            serializer = QuadratCollectionSerializer(
                data=quadrat_collection_data, context=self.context
            )
            if serializer.is_valid() is False:
                raise ValidationError(serializer.errors)

            return serializer.save()

    def get_or_create_bleaching_quadrat_collection(self, quadrat_collection_id, sample_unit_method_id=None):
        bleaching_quadrat_collection_data = {"quadrat": quadrat_collection_id, "id": sample_unit_method_id}
        return self.get_or_create(
            BleachingQuadratCollection,
            BleachingQuadratCollectionSerializer,
            bleaching_quadrat_collection_data,
        )

    def create_obs_quadrat_benthic_percent(self, bleaching_quadrat_collection_id):
        observation_benthic_percent_covered_data = []
        observations_data = get_obs_quadrat_benthic_percent_data(
            self.collect_record, bleaching_quadrat_collection_id
        )
        if not observations_data:
            return observation_benthic_percent_covered_data

        for observation_data in observations_data:
            observation_data["id"] = uuid.uuid4()
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
                {
                    "obs_colonies_bleached": [
                        _(u"Colonies bleached observations are required.")
                    ]
                }
            )

        for observation_data in observations_data:
            observation_data["id"] = uuid.uuid4()
            serializer = ObsColoniesBleachedSerializer(
                data=observation_data, context=self.context
            )
            if serializer.is_valid() is False:
                raise ValidationError(serializer.errors)

            observation_benthic_percent_covered_data.append(serializer.save())

        return observation_benthic_percent_covered_data

    def write(self):
        sample_unit_method_id = self.get_sample_unit_method_id()
        sample_event = self.get_or_create_sample_event()
        quadrat_collection = self.get_or_create_quadrat_collection(sample_event.id)
        bleaching_quadrat_collection = self.get_or_create_bleaching_quadrat_collection(
            quadrat_collection.id,
            sample_unit_method_id
        )
        _ = self.create_observers(bleaching_quadrat_collection.id)
        _ = self.create_obs_quadrat_benthic_percent(bleaching_quadrat_collection.id)
        _ = self.create_obs_colonies_bleached(bleaching_quadrat_collection.id)
