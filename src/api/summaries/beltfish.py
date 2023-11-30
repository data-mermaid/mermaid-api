from functools import lru_cache
from itertools import product
import pandas as pd

from ..models import BeltFishObsSQLModel, FishGroupTrophic, FishFamily


# NULL AS id,
# beltfish_su.pseudosu_id,
# project_id,
# project_name,
# project_status,
# project_notes,
# project_admins,
# contact_link,
# tags,
# site_id,
# site_name,
# location,
# longitude,
# latitude,
# site_notes,
# country_id,
# country_name,
# reef_type,
# reef_zone,
# reef_exposure,
# management_id,
# management_name,
# management_name_secondary,
# management_est_year,
# management_size,
# management_parties,
# management_compliance,
# management_rules,
# management_notes,
# sample_event_id,
# sample_date,
# sample_event_notes,
# depth,
# transect_number,
# transect_len_surveyed,
# data_policy_beltfish,
# beltfish_su.sample_unit_ids,
# label,
# relative_depth,
# sample_time,
# observers,
# current_name,
# tide_name,
# visibility_name,
# sample_unit_notes,
# reef_slope,
# transect_width_name,
# size_bin,

# total_abundance,
# biomass_kgha,
# biomass_kgha_trophic_group,
# biomass_kgha_trophic_group_zeroes,
# biomass_kgha_fish_family,
# biomass_kgha_fish_family_zeroes



# GROUP BY

# pseudosu_id,
# beltfish_obs.project_id,
# beltfish_obs.project_name,
# beltfish_obs.project_status,
# beltfish_obs.project_notes,
# beltfish_obs.project_admins,
# beltfish_obs.contact_link,
# beltfish_obs.tags,
# beltfish_obs.site_id,
# beltfish_obs.site_name,
# beltfish_obs.location,
# beltfish_obs.longitude,
# beltfish_obs.latitude,
# beltfish_obs.site_notes,
# beltfish_obs.country_id,
# beltfish_obs.country_name,
# beltfish_obs.reef_type,
# beltfish_obs.reef_zone,
# beltfish_obs.reef_exposure,
# beltfish_obs.management_id,
# beltfish_obs.management_name,
# beltfish_obs.management_name_secondary,
# beltfish_obs.management_est_year,
# beltfish_obs.management_size,
# beltfish_obs.management_parties,
# beltfish_obs.management_compliance,
# beltfish_obs.management_rules,
# beltfish_obs.management_notes,
# beltfish_obs.sample_event_id,
# beltfish_obs.sample_date,
# beltfish_obs.sample_event_notes,
# beltfish_obs.depth,
# beltfish_obs.transect_number,
# beltfish_obs.transect_len_surveyed,
# beltfish_obs.data_policy_beltfish


@lru_cache
def beltfish_obs(project_id):
    return pd.DataFrame.from_records(
        BeltFishObsSQLModel.objects.all().sql_table(project_id=project_id).values()
    )


def fish_trophic_group_by_sample_unit(project_id):
    obs = beltfish_obs(project_id)
    df = obs.groupby(["pseudosu_id", "trophic_group"])["biomass_kgha"].sum().reset_index()
    df["biomass_kgha"].fillna(0.0, inplace=True)
    return df


def fish_family_group_by_sample_unit(project_id):
    obs = beltfish_obs(project_id)
    df = obs.groupby(["pseudosu_id", "fish_family"])["biomass_kgha"].sum().reset_index()
    df["biomass_kgha"].fillna(0.0, inplace=True)
    return df





@lru_cache
def fish_trophic_group():
    return pd.DataFrame.from_records(FishGroupTrophic.objects.all().values())

@lru_cache
def fish_families():
    return pd.DataFrame.from_records(FishFamily.objects.all().values())


@lru_cache
def beltfish_su_tg_all(project_id):
    obs = beltfish_obs(project_id).copy()
    trophic_group = fish_trophic_group().copy()
    unique_pseudosu_ids = obs['pseudosu_id'].unique()
    unique_fish_families = trophic_group['name'].unique()
    combinations = product(unique_pseudosu_ids, unique_fish_families)
    return  pd.DataFrame(combinations, columns=['pseudosu_id', 'trophic_group'])


@lru_cache
def beltfish_su_tg(project_id):
    obs = beltfish_obs(project_id).copy()
    result = obs.groupby(['pseudosu_id', 'trophic_group'], as_index=False).agg(
        biomass_kgha=('biomass_kgha', 'sum')
    )
    result['biomass_kgha'] = result['biomass_kgha'].fillna(0)
    return result


def jsonb_object_agg(series):
    return series.apply(lambda x: round(x, 2) if pd.notnull(x) else x).to_dict()


def beltfish_tg(project_id):
    _beltfish_su_tg_all = beltfish_su_tg_all(project_id).copy()
    _beltfish_su_tg = beltfish_su_tg(project_id).copy()

    beltfish_su_tg_zeroes = pd.merge(
        _beltfish_su_tg_all[['pseudosu_id', 'trophic_group']],
        _beltfish_su_tg,
        on=['pseudosu_id', 'trophic_group'],
        how='left'
    )
    beltfish_su_tg_zeroes['biomass_kgha'] = beltfish_su_tg_zeroes['biomass_kgha'].fillna(0)

    # Aggregate to create biomass_kgha_trophic_group
    beltfish_tg = _beltfish_su_tg.groupby('pseudosu_id').apply(
        lambda x: jsonb_object_agg(x.set_index('trophic_group')['biomass_kgha'])
    ).reset_index().rename(columns={0: 'biomass_kgha_trophic_group'})

    # Aggregate to create biomass_kgha_trophic_group_zeroes
    beltfish_tg_zeroes_agg = beltfish_su_tg_zeroes.groupby('pseudosu_id').apply(
        lambda x: jsonb_object_agg(x.set_index('trophic_group')['biomass_kgha'])
    ).reset_index().rename(columns={0: 'biomass_kgha_trophic_group_zeroes'})

    # Combine both DataFrames
    return pd.merge(beltfish_tg, beltfish_tg_zeroes_agg, on='pseudosu_id')



@lru_cache
def beltfish_su_family_all(project_id):
    obs = beltfish_obs(project_id).copy()
    fish_family = fish_families().copy()
    unique_pseudosu_ids = obs['pseudosu_id'].unique()
    unique_fish_families = fish_family['name'].unique()
    combinations = product(unique_pseudosu_ids, unique_fish_families)
    return  pd.DataFrame(combinations, columns=['pseudosu_id', 'fish_family'])

@lru_cache
def beltfish_su_family(project_id):
    obs = beltfish_obs(project_id).copy()
    beltfish_su_family = obs.groupby(['pseudosu_id', 'fish_family'], as_index=False).agg(
        biomass_kgha=('biomass_kgha', 'sum')
    )
    beltfish_su_family['biomass_kgha'] = beltfish_su_family['biomass_kgha'].fillna(0)
    return beltfish_su_family
    

def beltfish_families(project_id):
    _beltfish_su_family = beltfish_su_family(project_id).copy()
    _beltfish_su_family_all = beltfish_su_family_all(project_id).copy()
    # Assuming beltfish_su_family and beltfish_su_family_all are already defined

    # Create beltfish_su_family_zeroes DataFrame
    beltfish_su_family_zeroes = pd.merge(
        _beltfish_su_family_all[['pseudosu_id', 'fish_family']],
        _beltfish_su_family,
        on=['pseudosu_id', 'fish_family'],
        how='left'
    )
    beltfish_su_family_zeroes['biomass_kgha'] = beltfish_su_family_zeroes['biomass_kgha'].fillna(0)

    # Define a function to replicate jsonb_object_agg behavior
    def jsonb_object_agg(series):
        return series.apply(lambda x: round(x, 2)).to_dict()

    # Apply aggregation to create biomass_kgha_fish_family
    beltfish_families = _beltfish_su_family.groupby('pseudosu_id').apply(lambda x: jsonb_object_agg(x.set_index('fish_family')['biomass_kgha'])).reset_index()
    beltfish_families.rename(columns={0: 'biomass_kgha_fish_family'}, inplace=True)

    # Apply aggregation to create biomass_kgha_fish_family_zeroes
    beltfish_families_zeroes = beltfish_su_family_zeroes.groupby('pseudosu_id').apply(lambda x: jsonb_object_agg(x.set_index('fish_family')['biomass_kgha'])).reset_index()
    beltfish_families_zeroes.rename(columns={0: 'biomass_kgha_fish_family_zeroes'}, inplace=True)

    # Merging the dataframes if needed
    return pd.merge(beltfish_families, beltfish_families_zeroes, on='pseudosu_id')


def beltfish_observers(project_id):
    obs = beltfish_obs(project_id).copy()
    beltfish_obs_expanded = obs.explode('observers')
    print(f"beltfish_obs_expanded: {beltfish_obs_expanded}")

    # Group by pseudosu_id and aggregate the observers
    return beltfish_obs_expanded.groupby('pseudosu_id')['observers'].agg(lambda x: list(x.dropna().unique())).reset_index()



def here(project_id):

    # Retrieve data using existing functions
    beltfish_su_base = beltfish_obs(project_id)  # Assuming project_id is defined
    beltfish_tg_df = beltfish_tg(project_id)
    beltfish_families_df = beltfish_families(project_id)
    # beltfish_observers_df = beltfish_observers(project_id)

    # Additional Aggregations on beltfish_su_base if needed
    # Depending on the structure of beltfish_su_base, you might need to perform additional aggregations here

    # Joining DataFrames
    beltfish_su = pd.merge(beltfish_su_base, beltfish_tg_df, on='pseudosu_id', how='inner')
    beltfish_su = pd.merge(beltfish_su, beltfish_families_df, on='pseudosu_id', how='inner')
    # beltfish_su = pd.merge(beltfish_su, beltfish_observers_df, on='pseudosu_id', how='inner')

    # beltfish_su now contains the joined data similar to your SQL query

    return beltfish_su
