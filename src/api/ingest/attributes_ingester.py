import csv
import datetime

from django.db import transaction

from api.models import (
    APPROVAL_STATUSES,
    BenthicAttribute,
    FishFamily,
    FishGenus,
    FishGroupFunction,
    FishGroupSize,
    FishGroupTrophic,
    FishSpecies,
    Region,
)
from api.utils import castutils


class BaseAttributeIngester(object):
    approval_status = APPROVAL_STATUSES[0][0]

    def __init__(self, file_obj):
        self.log = []
        self.regions = {r.name.lower(): r for r in Region.objects.all()}
        self._file = file_obj

    def _map_field(self, key, val, field_map, lookups, casts):
        val = val.strip()
        mapped_key = field_map.get(key)

        if mapped_key in lookups:
            if val:
                _val = lookups[field_map[key]][val]
            else:
                _val = val
        else:
            _val = val

        if mapped_key in casts:
            cast = casts.get(mapped_key)
            kwargs = cast.get("kwargs") or dict()
            _val = cast["fx"](_val, **kwargs)

        return _val

    def _map_fields(self, record, field_map, lookups=None, casts=None):
        lookups = lookups or dict()
        casts = casts or dict()
        mapped_rec = {}

        for key, val in record.items():
            mapped_key = field_map.get(key)
            if mapped_key is None:
                continue
            mapped_rec[field_map[key]] = self._map_field(
                key, val, field_map, lookups, casts
            )

        mapped_rec["status"] = self.approval_status
        return mapped_rec

    def write_log(self, action, message):
        timestamp = datetime.datetime.now().isoformat()
        log_msg = f"{action} [{timestamp}] {message}"
        self.log.append(log_msg)

    def _update_regions(self, attribute, region_names, is_combined=True):
        new_regions = [
            self.regions.get(region.strip().lower())
            for region in region_names.split(",")
        ]

        existing_regions = set(attribute.regions.all())
        if existing_regions == set(new_regions):
            return False, None

        existing_region_names = ",".join([er.name for er in existing_regions])
        if is_combined:
            combined_regions = set(existing_regions).union(new_regions)
        else:
            combined_regions = new_regions

        updates = (
            f"regions: {existing_region_names} -> {[f.name for f in combined_regions]}"
        )

        attribute.regions.clear()
        attribute.regions.set(combined_regions)

        return True, updates


class BenthicIngester(BaseAttributeIngester):
    ERROR = "ERROR"
    EXISTING_BENTHIC = "EXISTING_BENTHIC"
    NEW_BENTHIC = "NEW_BENTHIC"
    DUPLICATE_BENTHIC = "DUPLICATE_BENTHIC"
    UPDATE_BENTHIC = "UPDATE_BENTHIC"

    benthic_field_map = {
        "level1": "level1",
        "level2": "level2",
        "level3": "level3",
        "level4": "level4",
        "regions": "regions",
    }

    def __init__(self, file_obj):
        super().__init__(file_obj)
        self.benthic_lookups = self._create_benthic_lookups()

    def _create_benthic_lookups(self):
        return dict()

    def _ingest_benthic(self, row):
        benthic_row = self._map_fields(
            row, self.benthic_field_map, self.benthic_lookups
        )

        region_names = benthic_row.get("regions")
        level1 = benthic_row.get("level1")
        level2 = benthic_row.get("level2")
        level3 = benthic_row.get("level3")
        level4 = benthic_row.get("level4")

        if not level1:
            return

        try:
            parent1 = BenthicAttribute.objects.get(name__iexact=level1)
            has_region_edits, region_updates = self._update_regions(
                parent1, region_names
            )
            if has_region_edits:
                self.write_log(
                    self.UPDATE_BENTHIC, f"Level 1 - {parent1.name}: {region_updates}"
                )
            else:
                self.write_log(self.EXISTING_BENTHIC, f"Level 1 - {parent1.name}")
        except BenthicAttribute.DoesNotExist:
            parent1 = BenthicAttribute.objects.create(name=level1, status=self.approval_status)
            self._update_regions(parent1, region_names)
            self.write_log(self.NEW_BENTHIC, f"Level 1 - {parent1.name}")

        if not level2:
            return

        try:
            parent2 = BenthicAttribute.objects.get(name__iexact=level2, parent=parent1)
            has_region_edits, region_updates = self._update_regions(
                parent2, region_names
            )
            if has_region_edits:
                self.write_log(
                    self.UPDATE_BENTHIC,
                    f"Level 1 - {parent1.name} - Level 2 - {parent2.name}: {region_updates}",
                )
            else:
                self.write_log(
                    self.EXISTING_BENTHIC,
                    f"Level 1 - {parent1.name} - Level 2 - {parent2.name}",
                )
        except BenthicAttribute.DoesNotExist:
            parent2 = BenthicAttribute.objects.create(name=level2, parent=parent1, status=self.approval_status)
            self._update_regions(parent2, region_names)
            self.write_log(
                self.EXISTING_BENTHIC,
                f"Level 1 - {parent1.name} - Level 2 - {parent2.name}",
            )

        if not level3:
            return

        try:
            parent3 = BenthicAttribute.objects.get(name__iexact=level3, parent=parent2)
            has_region_edits, region_updates = self._update_regions(
                parent3, region_names
            )
            if has_region_edits:
                self.write_log(
                    self.UPDATE_BENTHIC,
                    f"Level 1 - {parent1.name} - Level 2 - {parent2.name} - Level 3 - {parent3.name}: {region_updates}",
                )
            else:
                self.write_log(
                    self.EXISTING_BENTHIC,
                    f"Level 1 - {parent1.name} - Level 2 - {parent2.name} - Level 3 - {parent3.name}",
                )
        except BenthicAttribute.DoesNotExist:
            parent3 = BenthicAttribute.objects.create(name=level3, parent=parent2, status=self.approval_status)
            self._update_regions(parent3, region_names)
            self.write_log(
                self.NEW_BENTHIC,
                f"Level 1 - {parent1.name} - Level 2 - {parent2.name} - Level 3 - {parent3.name}",
            )

        if not level4:
            return

        try:
            parent4 = BenthicAttribute.objects.get(name__iexact=level4, parent=parent3)
            has_region_edits, region_updates = self._update_regions(
                parent4, region_names
            )
            if has_region_edits:
                self.write_log(
                    self.UPDATE_BENTHIC,
                    f"Level 1 - {parent1.name} - Level 2 - {parent2.name} - Level 3 - {parent3.name} - Level 4 - {parent4.name}: {region_updates}",
                )
            else:
                self.write_log(
                    self.EXISTING_BENTHIC,
                    f"Level 1 - {parent1.name} - Level 2 - {parent2.name} - Level 3 - {parent3.name} - Level 4 - {parent4.name}",
                )
        except BenthicAttribute.DoesNotExist:
            parent4 = BenthicAttribute.objects.create(name=level4, parent=parent3, status=self.approval_status)
            self._update_regions(parent3, region_names)
            self.write_log(
                self.NEW_BENTHIC,
                f"Level 1 - {parent1.name} - Level 2 - {parent2.name} - Level 3 - {parent3.name} - Level 4 - {parent4.name}",
            )

    def ingest(self, dry_run=False):
        self.log = []
        csvreader = csv.DictReader(self._file, delimiter=",")
        n = 2
        is_successful = True
        for row in csvreader:
            try:
                with transaction.atomic():
                    sid = transaction.savepoint()
                    self._ingest_benthic(row)

                    if dry_run or is_successful is False:
                        transaction.savepoint_rollback(sid)
                    else:
                        transaction.savepoint_commit(sid)

            except Exception as err:
                transaction.savepoint_rollback(sid)
                err_msg = f"Row {n} - {str(err)}"
                self.write_log(self.ERROR, err_msg)
                is_successful = False
            finally:
                n = n + 1

        return is_successful, self.log


class FishIngester(BaseAttributeIngester):
    ERROR = "ERROR"
    EXISTING_FAMILY = "EXISTING_FAMILY"
    NEW_FAMILY = "NEW_FAMILY"

    EXISTING_GENUS = "EXISTING_GENUS"
    NEW_GENUS = "NEW_GENUS"
    DUPLICATE_GENUS = "DUPLICATE_GENUS"

    EXISTING_SPECIES = "EXISTING_SPECIES"
    NEW_SPECIES = "NEW_SPECIES"
    DUPLICATE_SPECIES = "DUPLICATE_SPECIES"
    UPDATE_SPECIES = "UPDATE_SPECIES"

    approval_status = APPROVAL_STATUSES[0][0]

    fish_family_field_map = {"Family": "name"}

    fish_genus_field_map = {"Genus": "name"}

    fish_species_field_map = {
        "Species": "name",
        "a": "biomass_constant_a",
        "b": "biomass_constant_b",
        "c": "biomass_constant_c",
        "Vulnerability": "vulnerability",
        "Maxlength": "max_length",
        "Max_length_type": "max_length_type",
        "Trophic_group": "trophic_group",
        "Primary_functional_group": "functional_group",
        "Group_size": "group_size",
        "Trophic_level": "trophic_level",
        "regions": "regions",
    }

    def __init__(self, file_obj):
        super().__init__(file_obj)

        # Placeholders until needed
        self.fish_family_lookups = dict()
        self.fish_genus_lookups = dict()

        self.fish_species_lookups = self._create_fish_species_lookups()
        self.fish_species_casts = self._get_model_casts(FishSpecies)

    def _get_model_casts(self, model_cls):
        fields = model_cls._meta.get_fields()
        casts = dict()

        for field in fields:

            if field.get_internal_type() == "DecimalField":
                kwargs = dict(
                    max_digits=field.max_digits, precision=field.decimal_places
                )
                casts[field.name.lower()] = dict(fx=castutils.to_number, kwargs=kwargs)

        return casts

    def _create_fish_species_lookups(self):
        fish_group_sizes = {fg.name.lower(): fg for fg in FishGroupSize.objects.all()}
        fish_group_trophics = {
            fgt.name.lower(): fgt for fgt in FishGroupTrophic.objects.all()
        }
        fish_group_functions = {
            fgf.name.lower(): fgf for fgf in FishGroupFunction.objects.all()
        }

        return dict(
            group_size=fish_group_sizes,
            trophic_group=fish_group_trophics,
            functional_group=fish_group_functions,
        )

    def ingest(self, dry_run=False):
        self.log = []
        csvreader = csv.DictReader(self._file, delimiter=",")
        n = 2
        is_successful = True
        for row in csvreader:
            try:
                with transaction.atomic():
                    sid = transaction.savepoint()
                    fish_family = self._ingest_fish_family(row)
                    fish_genus = self._ingest_fish_genus(row, fish_family=fish_family)
                    self._ingest_fish_species(row, fish_genus=fish_genus)

                    if dry_run or is_successful is False:
                        transaction.savepoint_rollback(sid)
                    else:
                        transaction.savepoint_commit(sid)

            except Exception as err:
                transaction.savepoint_rollback(sid)
                err_msg = f"Row {n} - {str(err)}"
                self.write_log(self.ERROR, err_msg)
                is_successful = False
            finally:
                n = n + 1

        return is_successful, self.log

    def _ingest_fish_family(self, row):
        family_row = self._map_fields(
            row, self.fish_family_field_map, self.fish_family_lookups
        )
        family_name = family_row.get("name")

        fish_family = None
        try:
            fish_family = FishFamily.objects.get(name__iexact=family_name)
            self.write_log(self.EXISTING_FAMILY, family_name)
        except FishFamily.DoesNotExist:
            fish_family = FishFamily.objects.create(**family_row)
            self.write_log(self.NEW_FAMILY, family_name)
        except FishFamily.MultipleObjectsReturned:
            self.write_log(self.DUPLICATE_FAMILY, family_name)

        return fish_family

    def _ingest_fish_genus(self, row, fish_family):
        genus_row = self._map_fields(
            row, self.fish_genus_field_map, self.fish_genus_lookups
        )
        genus_name = genus_row["name"]
        try:
            genus = FishGenus.objects.get(name__iexact=genus_name, family=fish_family)
            self.write_log(self.EXISTING_GENUS, genus_name)
        except FishGenus.DoesNotExist:
            genus = FishGenus.objects.create(family=fish_family, **genus_row)
            self.write_log(self.NEW_GENUS, genus_name)
        except FishGenus.MultipleObjectsReturned:
            self.write_log(self.DUPLICATE_GENUS, genus_name)

        return genus

    def _ingest_fish_species(self, row, fish_genus):
        species_row = self._map_fields(
            row,
            self.fish_species_field_map,
            lookups=self.fish_species_lookups,
            casts=self.fish_species_casts,
        )
        species_name = species_row["name"]
        genus_name = fish_genus.name
        try:
            species = FishSpecies.objects.get(
                name__iexact=species_name, genus=fish_genus
            )
            has_edits = False
            region_names = species_row.pop("regions")
            updates = []
            for k, v in species_row.items():
                original_val = getattr(species, k)
                if hasattr(species, k) and original_val != v:
                    setattr(species, k, v)
                    updates.append(f"{k}: {original_val} -> {v}")
                    has_edits = True

            has_region_edits, region_updates = self._update_regions(
                species, region_names, is_combined=False
            )
            if has_region_edits:
                updates.append(region_updates)

            if has_edits or has_region_edits:
                species.save()
                self.write_log(
                    self.UPDATE_SPECIES,
                    f"{genus_name}-{species_name}: {', '.join(updates)}",
                )
            else:
                self.write_log(self.EXISTING_SPECIES, f"{genus_name}-{species_name}")

        except FishSpecies.DoesNotExist:
            region_names = species_row.pop("regions")
            species = FishSpecies.objects.create(genus=fish_genus, **species_row)
            self._update_regions(species, region_names, is_combined=False)

            self.write_log(self.NEW_SPECIES, f"{genus_name}-{species_name}")
        except FishSpecies.MultipleObjectsReturned:
            self.write_log(self.DUPLICATE_SPECIES, species_name)
