#!/usr/bin/env python3

from flask import json, current_app as app
import requests


class GeoServiceClient:
    geo_service_url = ""
    countries = []

    def __init__(self, host: str):
        self.geo_service_url = "{}".format(host)

    def validate_countries(self, country_list):
        r = requests.get(self.geo_service_url)
        app.logger.debug(r.text)

        if not r.json():
            return False

        geo_countries = r.json()

        for country in geo_countries:
            if country["id"] in country_list:
                self.countries.append(country["id"])

        return self.countries

