import os
import requests
import csv
from contextlib import closing
from django.conf import settings
from django.core.management.base import BaseCommand

from api.models import (FishFamily, FishGenus, FishSpecies, BaseAttributeModel, APPROVAL_STATUSES)


def map_fields(record, field_map):
    mapped_rec = {}
    for k, v in record.items():
        if k in field_map:
            mapped_rec[field_map[k]] = v
    mapped_rec['status'] = APPROVAL_STATUSES[0][0]
    return mapped_rec


class Command(BaseCommand):
    help = """Version of refresh_fish meant for ad hoc db querying/editing.
    Just uses names for determining new/update status; migrations for schema changes unnecessary."""

    FISH_FAMILY_FIELD_MAP = {
        'Family': 'name',
    }
    FISH_GENUS_FIELD_MAP = {
        'Genus': 'name',
    }
    FISH_SPECIES_FIELD_MAP = {
        'Species': 'name',
        # 'a': 'biomass_constant_a',
        # 'b': 'biomass_constant_b',
        # 'c': 'biomass_constant_c',
        # 'Vulnerability': 'vulnerability',
        # 'Maxlength': 'max_length',
        # 'Max_length_type': 'max_length_type',
        # 'Trophic_group': 'trophic_group',
        # 'Primary_functional_group': 'functional_group',
        # 'Group_size': 'group_size',
        # 'Trophic_level': 'trophic_level',
    }

    def __init__(self):
        super(Command, self).__init__()
        # self.source = 'http://datamermaid.org/listab_2018_August_data.csv'
        self.source = os.path.join(settings.BASE_DIR, 'data', 'listab_2018_August_data.csv')
        self.moved_template = 'name: %s existing parent: %s new parent: %s'
        self.mode = 'f'

    def add_arguments(self, parser):
        # f = family
        # g = genus
        # s = species
        # d = delete
        parser.add_argument('mode', type=str, nargs='?', choices=['f', 'g', 's', 'd'], default='f')

    def handle(self, *args, **options):
        self.mode = options.get('mode')

        # with closing(requests.get(self.source, stream=True)) as fishdata:
        with open(self.source) as fishdata:
            # csvreader = csv.DictReader(fishdata.iter_lines(), delimiter=',')
            csvreader = csv.DictReader(fishdata, delimiter=',')
            new_families = set()
            dup_families = set()
            new_genera = set()
            dup_genera = set()
            moved_genera = {}
            new_species = set()
            dup_species = set()
            moved_species = {}

            all_new_families = set()
            all_new_genera = set()
            all_new_species = set()

            for row in csvreader:
                family_row = map_fields(row, self.FISH_FAMILY_FIELD_MAP)
                all_new_families.add(family_row['name'])
                try:
                    family = FishFamily.objects.get(**family_row)
                except FishFamily.DoesNotExist:
                    new_families.add(family_row['name'])
                except FishFamily.MultipleObjectsReturned:
                    dup_families.add(family_row['name'])

                genus_row = map_fields(row, self.FISH_GENUS_FIELD_MAP)
                all_new_genera.add(genus_row['name'])
                try:
                    genus = FishGenus.objects.get(**genus_row)
                    if family_row['name'] != genus.family.name:
                        moved_genera[genus.pk] = (genus.name, genus.family.name, family_row['name'])
                except FishGenus.DoesNotExist:
                    new_genera.add(genus_row['name'])
                except FishGenus.MultipleObjectsReturned:
                    dup_genera.add(genus_row['name'])

                species_row = map_fields(row, self.FISH_SPECIES_FIELD_MAP)
                all_new_species.add(species_row['name'])
                try:
                    species = FishSpecies.objects.get(**species_row)
                    if genus_row['name'] != species.genus.name:
                        moved_species[species.pk] = (species.name, species.genus.name, genus_row['name'])
                except FishSpecies.DoesNotExist:
                    new_species.add(species_row['name'])
                except FishSpecies.MultipleObjectsReturned:
                    dup_species.add(species_row['name'])

            if self.mode == 'f':
                print('\nnew_families:')
                print("\n".join(sorted(new_families)))
                print('\ndup_families:')
                print("\n".join(sorted(dup_families)))
            elif self.mode == 'g':
                print('\nnew_genera:')
                print("\n".join(sorted(new_genera)))
                print('\ndup_genera:')
                print("\n".join(sorted(dup_genera)))
                print('\ngenera with changed family:')
                print("\n".join([self.moved_template % g for g in sorted(moved_genera.values())]))
            elif self.mode == 's':
                print('\nnew_species:')
                print("\n".join(sorted(new_species)))
                print('\ndup_species:')
                print("\n".join(sorted(dup_species)))
                print('\nspecies with changed genus:')
                print("\n".join([self.moved_template % s for s in sorted(moved_species.values())]))
            elif self.mode == 'd':
                print('\nfamilies to delete:')
                for f in FishFamily.objects.all().values():
                    if f['name'] not in all_new_families:
                        print(f['name'])
                print('\ngenera to delete:')
                for g in FishGenus.objects.all().values():
                    if g['name'] not in all_new_genera:
                        print(g['name'])
                print('\nspecies to delete:')
                for s in FishSpecies.objects.all().values():
                    if s['name'] not in all_new_species:
                        print(s['name'])
