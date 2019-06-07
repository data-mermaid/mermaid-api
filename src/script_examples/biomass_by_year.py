# Example scripts should be run with local interpreter with scientific stack installed
import requests
import matplotlib.pyplot as plt
import numpy as np
from utilities import *


plt.style.use('ggplot')

client = requests.session()
headers = api_headers(client)

if headers:
    projects = client.get('%sprojects/' % api, **headers).json()
    fish_attributes = client.get('%sfishattributes/' % api, **headers).json()
    choices = client.get('%schoices/' % api, **headers).json()
    widths = lookup('name', 'belttransectwidths', choices)

    project = lookup('name', project_name, projects['results'])
    if project:
        endpoints = find_endpoints(project, 'http')

        # To hit a project endpoint, use endpoints[endpoint_name]
        project_beltfishs = client.get(endpoints['beltfishs'], **headers).json()
        project_beltfish_transects = client.get(endpoints['fishbelttransects'], **headers).json()
        sample_events = client.get(endpoints['sampleevents'], **headers).json()

        # EXAMPLE: SUMMARIZE BIOMASS PER YEAR
        biomass_by_year = {}
        # TODO: wrap this in a function that calls paginated endpoint (instead of using large limit) until next is None
        ep = '%s&limit=1000' % endpoints['obstransectbeltfishs']
        belt_fish_observations = client.get(ep, **headers).json()
        for obs in belt_fish_observations['results']:
            year = get_year_from_obs(obs, project_beltfishs, project_beltfish_transects, sample_events)
            biomass = get_biomass_kg_ha(obs, fish_attributes, project_beltfishs, project_beltfish_transects, widths)
            biomass_by_year[year] = biomass_by_year.get(year, 0) + biomass
        biomass_by_year_sorted = sorted(biomass_by_year.items())

        x, y = zip(*biomass_by_year_sorted)
        plt.xticks(range(min(x) - 1, max(x) + 1))
        plt.xlabel('Year')
        plt.ylabel('Biomass (kg/ha)')
        plt.plot(x, y, '-o')
        # calc the trendline
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        plt.plot(x, p(x), "r--")
        # the line equation:
        print "y=%.6fx+(%.6f)" % (z[0], z[1])
        plt.show()

    else:
        print('No project named %s' % project_name)
else:
    print('Error getting access token')
