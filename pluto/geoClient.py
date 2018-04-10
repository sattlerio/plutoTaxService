#!/usr/bin/env python3

from flask import json, current_app as app
import requests


class GeoServiceClient:
    geo_service_url = ""

    def __init__(self, host: str):
        self.geo_service_url = "{}".format(host)

    def validate_countries(self, country_list):
        countries = []
        r = requests.get(self.geo_service_url)

        if not r.json():
            return False

        geo_countries = r.json()

        for country in geo_countries:
            if country["id"] in country_list:
                countries.append(country["id"])

        r.close()
        return countries

