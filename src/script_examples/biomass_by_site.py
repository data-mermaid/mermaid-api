# Example scripts should be run with local interpreter with scientific stack installed
import matplotlib.pyplot as plt
import numpy as np
import requests
from utilities import *

plt.style.use("ggplot")

client = requests.session()
headers = api_headers(client)

if headers:
    projects = client.get("%sprojects/" % api, **headers).json()
    fish_attributes = client.get("%sfishattributes/" % api, **headers).json()
    choices = client.get("%schoices/" % api, **headers).json()
    widths = lookup("name", "belttransectwidths", choices)

    project = lookup("name", project_name, projects["results"])
    if project:
        endpoints = find_endpoints(project, "http")

        # To hit a project endpoint, use endpoints[endpoint_name]
        project_beltfishs = client.get(endpoints["beltfishs"], **headers).json()
        project_beltfish_transects = client.get(endpoints["fishbelttransects"], **headers).json()
        sample_events = client.get(endpoints["sampleevents"], **headers).json()
        project_sites = client.get(endpoints["psites"], **headers).json()

        # EXAMPLE: SUMMARIZE BIOMASS PER SITE
        sitenames = [s["name"] for s in project_sites["results"]]
        biomass_per_site = {n: 0 for n in sitenames}
        # TODO: wrap this in a function that calls paginated endpoint (instead of using large limit) until next is None
        ep = "%s&limit=1000" % endpoints["obstransectbeltfishs"]
        belt_fish_observations = client.get(ep, **headers).json()
        for obs in belt_fish_observations["results"]:
            site = get_site_from_obs(
                obs, project_beltfishs, project_beltfish_transects, sample_events, project_sites
            )
            biomass_per_site[site["name"]] += get_biomass_kg_ha(
                obs, fish_attributes, project_beltfishs, project_beltfish_transects, widths
            )

        print("\n--- Project %s fish biomass by site ---" % project_name)
        for site, biomass in biomass_per_site.items():
            print("Site: %s  Biomass (kg/ha): %s" % (site, biomass))
            if biomass == 0:
                del biomass_per_site[site]

        biomass_per_site_sorted = sorted(biomass_per_site.items())
        x, y = zip(*biomass_per_site_sorted)
        plt.bar(x, y, align="center", alpha=0.5)
        plt.xticks(x, sitenames)
        plt.ylabel("Biomass (kg/ha)")
        plt.show()

    else:
        print("No project named %s" % project_name)
else:
    print("Error getting access token")
