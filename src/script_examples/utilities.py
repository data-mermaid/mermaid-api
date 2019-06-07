import requests
from settings import *


def api_headers(client):
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "audience": audience,
        "grant_type": grant_type
    }

    r = client.post('%s/oauth/token' % URL, data=payload)

    if r.status_code == requests.codes.ok:
        access_token = r.json()['access_token']
        headers = {'Authorization': 'Bearer %s' % access_token}
        # Now use the access token for every MERMAID API request by passing it in the headers
        return {'params': params, 'headers': headers}
    else:
        return None


def lookup(key, val, list):
    for item in list:
        if key in item and item[key] == val:
            return item
    return None


def find_endpoints(myDict, lookup):
    return_dict = {}
    for k in myDict:
        if isinstance(myDict[k], (int, long, float, complex)):
            continue
        if lookup in myDict[k]:
            return_dict[k] = myDict[k]
    return return_dict


def get_site_from_obs(obs, project_beltfishs, project_beltfish_transects, sample_events, project_sites):
    beltfish = lookup('id', obs['beltfish'], project_beltfishs['results'])
    beltfish_transect = lookup('id', beltfish['transect'], project_beltfish_transects['results'])
    sample_event = lookup('id', beltfish_transect['sample_event'], sample_events['results'])
    site = lookup('id', sample_event['site'], project_sites['results'])
    return site


def get_year_from_obs(obs, project_beltfishs, project_beltfish_transects, sample_events):
    beltfish = lookup('id', obs['beltfish'], project_beltfishs['results'])
    beltfish_transect = lookup('id', beltfish['transect'], project_beltfish_transects['results'])
    sample_event = lookup('id', beltfish_transect['sample_event'], sample_events['results'])
    yr = sample_event['sample_date'][0:4]
    return int(yr)


def get_biomass_kg_ha(obs, fish_attributes, project_beltfishs, project_beltfish_transects, widths):
    fish_attribute = lookup('id', obs['fish_attribute'], fish_attributes)
    beltfish = lookup('id', obs['beltfish'], project_beltfishs['results'])
    beltfish_transect = lookup('id', beltfish['transect'], project_beltfish_transects['results'])
    width = lookup('id', beltfish_transect['width'], widths['data'])

    if obs['include'] and fish_attribute and beltfish:
        size = float(obs['size'])
        count = obs['count']
        a = fish_attribute['biomass_constant_a'] or 0
        b = fish_attribute['biomass_constant_b'] or 0
        length = beltfish_transect['len_surveyed']
        width = width['val']

        biomass = count * (float(a) * pow(size, float(b))) / 1000.0
        area = (length * width) / 10000.0  # m2 to hectares
        return round(biomass / area, 2)

    return 0
