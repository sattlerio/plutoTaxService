#!/usr/bin/env python3
from flask import current_app as app
import requests


class GuardianClient:
    guardian_service_url = ""

    def __init__(self, host: str, user_uuid: str, company_id: str):
        self.guardian_service_url = "{}/{}/{}".format(host, user_uuid, company_id)

    def get_user_permission(self):
        r = requests.get(self.guardian_service_url)
        app.logger.debug(r.text)
        return r

    def validate_permission(self, permission: int) -> bool:
        if permission >= 0 and permission <= 2:
            return True
        else:
            return False
