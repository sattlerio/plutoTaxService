from flask import jsonify, request, Blueprint, Response, current_app as app
from pluto.models import *
from pluto.guardianClient import GuardianClient
from pluto.geoClient import GeoServiceClient
import uuid
import types

pluto = Blueprint('pluto', __name__)


@pluto.route('/ping', methods=['GET'])
def test():
    return "pong"


def _validate_request(user_uuid, company_id, transaction_id):
    guardian_client = GuardianClient(app.config.get("GUARDIAN_SERVICE"), user_uuid, company_id)
    response = guardian_client.get_user_permission()

    if not response and response.status_code != 200:
        app.logger.info(
            f"{transaction_id}: got aborted transaction as answer from Guardian with status {response.status_code}")

        if response.status_code == 401:
            status_code = 401
            message = "user has no permission"
        elif response.status_code == 404:
            status_code = 404
            message = "resource does not exist"
        else:
            status_code = 500
            message = "unkown error"

        return jsonify(
            status="ERROR",
            status_code=status_code,
            message=message,
            reques_id=transaction_id
        ), status_code

    data = response.json()
    if "status" in data and data["status"] == "OK":
        permission = data["data"]["user_permission"]
        app.logger.info(f"{transaction_id}: successfully got user permission from guardian --> {permission}")

        if not guardian_client.validate_permission(permission):
            return jsonify(
                status="ERROR",
                status_code=401,
                message="user has not the permission to create taxes",
                request_id=transaction_id
            ), 401

    else:
        app.logger.info(f"{transaction_id}: error during communication with guardian --> {response.json()}")
        return jsonify(
            status="ERROR",
            status_code=500,
            message="unkown response from guardian",
            request_id=transaction_id
        ), 500


@pluto.route("/test/<tax_id>/<company_id>", methods=["POST"])
def test_tax_configuration(tax_id, company_id):
    transaction_id = request.headers.get("x-transactionid", "")
    if not transaction_id:
        app.logger.info("no transaction id header present")
        transaction_id = str(uuid.uuid4())

    app.logger.info(f"{transaction_id}: got new transaction to fetch all taxes")

    if "x-user-id" not in request.headers or "x-user-uuid" not in request.headers:
        app.logger.info(f"{transaction_id}: user id and user uuid header not present")
        return jsonify(
            status="ERROR",
            message="please send your user as header",
            request_id=transaction_id,
            status_code=400
        ), 400

    user_uuid = request.headers.get("x-user-uuid")

    validation = _validate_request(user_uuid, company_id, transaction_id)
    if validation:
        return validation

    tax = Tax.query.filter_by(tax_uuid=tax_id).first_or_404()

    if not request.is_json and not request.json:
        app.logger.info(f"{transaction_id}: no json data submitted")
        return jsonify(
            status="ERROR",
            message="you have to submit a valid post json body",
            request_id=transaction_id,
            status_code=400
        ), 400

    post_data = request.json

    if not post_data or "tax_option" not in post_data or "country" not in post_data:
        app.logger.info("not a valid post request because of missing data")
        return jsonify(
            status="ERROR",
            message="please submit valid POST body",
            request_id=transaction_id,
            status_code=400
        ), 400

    if post_data["tax_option"] == "b2c":
        b2c = True
    else:
        b2c =False

    tax_value = tax.default_tax
    tax_name = ""

    if len(tax.tax_rules) >= 1:
        tx = TaxRule.query.filter_by(tax_id=tax.id).filter_by(b2c_rule=b2c).join(TaxRuleCountry).filter(TaxRuleCountry.country_id==post_data["country"])
        tx2 = TaxRule.query.filter_by(tax_id=tax.id).filter_by(b2c_rule=b2c).filter(~TaxRule.countries.any())
        if tx.count() == 1:
            rate = tx.first()
            tax_value = rate.value
            tax_name = rate.tax_rule_name
        elif tx2.count() == 1:
            rate = tx2.first()
            tax_value = rate.value
            tax_name = rate.tax_rule_name

    return jsonify(
        status="OK",
        status_code=200,
        tax_rate=float(tax_value),
        tax=tax_name,
        request_id=transaction_id
    ), 200


@pluto.route("/all/<company_id>")
def fetch_all_taxes(company_id):
    transaction_id = request.headers.get("x-transactionid", "")
    if not transaction_id:
        app.logger.info("no transaction id header present")
        transaction_id = str(uuid.uuid4())

    app.logger.info(f"{transaction_id}: got new transaction to fetch all taxes")

    if "x-user-id" not in request.headers or "x-user-uuid" not in request.headers:
        app.logger.info(f"{transaction_id}: user id and user uuid header not present")
        return jsonify(
            status="ERROR",
            message="please send your user as header",
            request_id=transaction_id,
            status_code=400
        ), 400

    user_uuid = request.headers.get("x-user-uuid")

    validation = _validate_request(user_uuid, company_id, transaction_id)
    if validation:
        return validation

    data = []
    for tax in Tax.query.filter_by(company_id=company_id).all():
        data.append({
            'name': tax.name,
            'default_rate': int(tax.default_tax),
            'default_rate_read': f"{tax.default_tax}%",
            'rules': len(tax.tax_rules),
            'tax_id': tax.tax_uuid
        })

    return jsonify(
        status="OK",
        message="successfully fetched taxes",
        data=data,
        status_code=200,
        transaction_id=transaction_id
    )


@pluto.route("/<tax_id>/<company_id>")
def fetch_tax_by_id(tax_id, company_id):
    transaction_id = request.headers.get("x-transactionid", "")
    if not transaction_id:
        app.logger.info("no transaction id header present")
        transaction_id = str(uuid.uuid4())

    app.logger.info(f"{transaction_id}: got new transaction to fetch all taxes")

    if "x-user-id" not in request.headers or "x-user-uuid" not in request.headers:
        app.logger.info(f"{transaction_id}: user id and user uuid header not present")
        return jsonify(
            status="ERROR",
            message="please send your user as header",
            request_id=transaction_id,
            status_code=400
        ), 400

    user_uuid = request.headers.get("x-user-uuid")

    validation = _validate_request(user_uuid, company_id, transaction_id)
    if validation:
        return validation
    
    tax = Tax.query.filter_by(tax_uuid=tax_id).filter_by(company_id=company_id).first_or_404()
    data = {
        'name': tax.name,
        'default_rate': int(tax.default_tax),
        'default_rate_read': f"{tax.default_tax}%",
        'rules': len(tax.tax_rules),
        'tax_id': tax.tax_uuid
    }
    
    return jsonify(
        status="OK",
        message="successfully fetched tax",
        data=data,
        status_code=200,
        transaction_id=transaction_id
    )


@pluto.route("/rule/configuration/data/<tax_id>/<company_id>")
def fetch_tax_configuration(tax_id, company_id):
    transaction_id = request.headers.get("x-transactionid", "")

    arg_tax_rule_id = request.args.get("tax_rule_id", False)

    if not transaction_id:
        app.logger.info("no transaction id header present")
        transaction_id = str(uuid.uuid4())

    app.logger.info(f"{transaction_id}: got new transaction to fetch all taxes")

    if "x-user-id" not in request.headers or "x-user-uuid" not in request.headers:
        app.logger.info(f"{transaction_id}: user id and user uuid header not present")
        return jsonify(
            status="ERROR",
            message="please send your user as header",
            request_id=transaction_id,
            status_code=400
        ), 400

    user_uuid = request.headers.get("x-user-uuid")

    validation = _validate_request(user_uuid, company_id, transaction_id)
    if validation:
        return validation

    tax = Tax.query.filter_by(tax_uuid=tax_id).filter_by(company_id=company_id).first_or_404()

    if arg_tax_rule_id:
        tax_groups = TaxRule.query.filter_by(tax_id=tax.id).filter_by(b2c_rule=False).filter(TaxRule.tax_rule_uuid != arg_tax_rule_id).all()
        b2c_tax_groups = TaxRule.query.filter_by(tax_id=tax.id).filter_by(b2c_rule=True).filter(TaxRule.tax_rule_uuid != arg_tax_rule_id).all()

        b2c_without_countries = count = TaxRule.query.filter_by(tax_id=tax.id).filter_by(b2c_rule=True).filter(TaxRule.tax_rule_uuid != arg_tax_rule_id).filter(~TaxRule.countries.any()).count()
        rules_without_countries = count = TaxRule.query.filter_by(tax_id=tax.id).filter_by(b2c_rule=False).filter(TaxRule.tax_rule_uuid != arg_tax_rule_id).filter(~TaxRule.countries.any()).count()
    else:
        tax_groups = TaxRule.query.filter_by(tax_id=tax.id).filter_by(b2c_rule=False).all()
        b2c_tax_groups = TaxRule.query.filter_by(tax_id=tax.id).filter_by(b2c_rule=True).all()

        b2c_without_countries = count = TaxRule.query.filter_by(tax_id=tax.id).filter_by(b2c_rule=True).filter(
            ~TaxRule.countries.any()).count()
        rules_without_countries = count = TaxRule.query.filter_by(tax_id=tax.id).filter_by(b2c_rule=False).filter(
            ~TaxRule.countries.any()).count()

    forbidden_regular_countries = []
    for rule in tax_groups:
        for country in rule.countries:
            forbidden_regular_countries.append(country.country_id)

    forbidden_b2c_countries = []
    for rule in b2c_tax_groups:
        for country in rule.countries:
            forbidden_b2c_countries.append(country.country_id)

    data = {
        'name': tax.name,
        'b2c_without_countries': b2c_without_countries,
        'rules_without_countries': rules_without_countries,
        'default_rate': int(tax.default_tax),
        'default_rate_read': f"{tax.default_tax}%",
        'tax_id': tax.tax_uuid
    }

    return jsonify(
        status="OK",
        message="successfully fetched tax",
        tax=data,
        used_regular_countries=forbidden_regular_countries,
        used_b2c_countries=forbidden_b2c_countries,
        status_code=200,
        transaction_id=transaction_id
    )


@pluto.route("/rules/<tax_id>/<company_id>")
def fetch_tax_rules(tax_id, company_id):
    transaction_id = request.headers.get("x-transactionid", "")
    if not transaction_id:
        app.logger.info("no transaction id header present")
        transaction_id = str(uuid.uuid4())

    app.logger.info(f"{transaction_id}: got new transaction to fetch tax per id  with rules")

    if "x-user-id" not in request.headers or "x-user-uuid" not in request.headers:
        app.logger.info(f"{transaction_id}: user id and user uuid header not present")
        return jsonify(
            status="ERROR",
            message="please send your user as header",
            request_id=transaction_id,
            status_code=400
        ), 400

    user_uuid = request.headers.get("x-user-uuid")

    validation = _validate_request(user_uuid, company_id, transaction_id)
    if validation:
        return validation

    tax = Tax.query.filter_by(tax_uuid=tax_id).filter_by(company_id=company_id).first_or_404()
    tax_data = {
        'name': tax.name,
        'default_rate': int(tax.default_tax),
        'default_rate_read': f"{tax.default_tax}%",
        'rules': len(tax.tax_rules),
        'tax_id': tax.tax_uuid
    }

    data_b2c = []
    data = []
    for rule in tax.tax_rules:
        countries = []
        for country in rule.countries:
            countries.append(country.country_id)
        if rule.b2c_rule:
            data_b2c.append({
                'rule_id': rule.tax_rule_uuid,
                'name': rule.tax_rule_name,
                'b2c_rule': rule.b2c_rule,
                'rule': float(rule.value),
                'human_rule': "{}%".format(rule.value),
                'countries': countries
            })
        else:
            data.append({
                'rule_id': rule.tax_rule_uuid,
                'name': rule.tax_rule_name,
                'b2c_rule': rule.b2c_rule,
                'rule': float(rule.value),
                'human_rule': "{}%".format(rule.value),
                'countries': countries
            })

    tax_data["data"] = data
    tax_data["data_b2c"] = data_b2c

    return jsonify(
        status="OK",
        message="successfully fetched tax",
        data=tax_data,
        status_code=200,
        transaction_id=transaction_id
    )


@pluto.route("/rule/<tax_rule_id>/<tax_id>/<company_id>")
def fetch_tax_rule_by_id(tax_rule_id, tax_id, company_id):
    transaction_id = request.headers.get("x-transactionid", "")
    if not transaction_id:
        app.logger.info("no transaction id header present")
        transaction_id = str(uuid.uuid4())

    app.logger.info(f"{transaction_id}: got new transaction to fetch tax per id  with rules")

    if "x-user-id" not in request.headers or "x-user-uuid" not in request.headers:
        app.logger.info(f"{transaction_id}: user id and user uuid header not present")
        return jsonify(
            status="ERROR",
            message="please send your user as header",
            request_id=transaction_id,
            status_code=400
        ), 400

    user_uuid = request.headers.get("x-user-uuid")

    validation = _validate_request(user_uuid, company_id, transaction_id)
    if validation:
        return validation

    tax = Tax.query.filter_by(tax_uuid=tax_id).filter_by(company_id=company_id).first_or_404()
    tax_rule = TaxRule.query.filter_by(tax_id=tax.id).filter_by(tax_rule_uuid=tax_rule_id).first_or_404()

    data = {
        "tax_rule_name": tax_rule.tax_rule_name,
        "tax_rule_uuid": tax_rule.tax_rule_uuid,
        "value": float(tax_rule.value),
        "b2c_rule": tax_rule.b2c_rule
    }

    countries = []
    for country in tax_rule.countries:
        countries.append(country.country_id)

    data = {
        "tax_rule_name": tax_rule.tax_rule_name,
        "tax_rule_uuid": tax_rule.tax_rule_uuid,
        "value": float(tax_rule.value),
        "b2c_rule": tax_rule.b2c_rule,
        "countries": countries
    }

    return jsonify(
        status="OK",
        message="successfully fetched tax",
        data=data,
        status_code=200,
        transaction_id=transaction_id
    )


@pluto.route("/<tax_id>/create/rule/<company_id>", methods=["POST", "PUT"])
def add_rule_to_tax(tax_id, company_id):
    transaction_id = request.headers.get("x-transactionid", "")
    if not transaction_id:
        app.logger.info("no transaction id header present")
        transaction_id = str(uuid.uuid4())

    app.logger.info(f"{transaction_id}: got new transaction to create rule for tax")

    arg_tax_rule_id = request.args.get("tax_rule_id", False)
    if request.method == "PUT" and not arg_tax_rule_id:
        return jsonify(
            status="ERROR",
            message="you have to submit the tax_rule_id for editing a tax rule",
            request_id=transaction_id,
            status_code=400
        ), 400

    if "x-user-id" not in request.headers or "x-user-uuid" not in request.headers:
        app.logger.info(f"{transaction_id}: user id and user uuid header not present")
        return jsonify(
            status="ERROR",
            message="please send your user as header",
            request_id=transaction_id,
            status_code=400
        ), 400

    user_id = request.headers.get("x-user-id")
    user_uuid = request.headers.get("x-user-uuid")

    app.logger.info(f"{transaction_id}: successfully read userid and useruuid from request")

    validation = _validate_request(user_uuid, company_id, transaction_id)
    if validation:
        return validation

    if not request.is_json and not request.json:
        app.logger.info(f"{transaction_id}: no json data submitted")
        return jsonify(
            status="ERROR",
            message="you have to submit a valid post json body",
            request_id=transaction_id,
            status_code=400
        ), 400

    tax = Tax.query.filter_by(tax_uuid=tax_id)
    if tax.count() != 1:
        return jsonify(
            status="ERROR",
            message="requested tax does not exist",
            request_id=transaction_id,
            status_code=404
        ), 404
    tax = tax.first()

    if request.method == "PUT":
        given_tax_rule = TaxRule.query.filter_by(tax_id=tax.id).filter_by(tax_rule_uuid=arg_tax_rule_id).first_or_404()

    post_data = request.json

    if not post_data or "rule_name" not in post_data or "value" not in post_data or "b2c_rule" not in post_data:
        app.logger.info("not a valid post request because of missing data")
        return jsonify(
            status="ERROR",
            message="please submit valid POST body",
            request_id=transaction_id,
            status_code=400
        ), 400

    countries = []
    if post_data["b2c_rule"]:
        b2c = True
        app.logger.info("request is for b2c")
        if "b2c_countries" in post_data:
            countries = post_data["b2c_countries"]
    else:
        b2c = False
        app.logger.info("request is for non b2c ")
        if "countries" in post_data:
            countries = post_data["countries"]

    if countries:
        if not isinstance(countries, list):
            return jsonify(
                status="ERROR",
                message="please submit a valid post body",
                request_id=transaction_id,
                status_code=400
            ), 400

        geo_client = GeoServiceClient(app.config.get("GEOSERVICE"))
        validated_countries = geo_client.validate_countries(countries)

        if not validated_countries:
            return jsonify(
                status="ERROR",
                message="the submitted data is not valid",
                request_id=transaction_id,
                status_code=400
            ), 400

        if request.method == "PUT":
            given_tax_rule.value = post_data["value"]
            given_tax_rule.tax_rule_name = post_data["rule_name"]
            given_tax_rule.b2c_rule = b2c
            db.session.add(given_tax_rule)

            for country in given_tax_rule.countries:
                db.session.delete(country)
        else:
            tax_rule = TaxRule(tax.id, post_data["value"], post_data["rule_name"], b2c)
            db.session.add(tax_rule)

        for country in validated_countries:
            count = TaxRule.query.filter_by(tax_id=tax.id).filter_by(b2c_rule=b2c).filter(TaxRule.countries.any(country_id=country)).count()
            if count == 0:
                trc = TaxRuleCountry(country)
                if request.method == "PUT":
                    given_tax_rule.countries.append(trc)
                else:
                    tax_rule.countries.append(trc)
            else:
                return jsonify(
                    status="ERROR",
                    status_code=400,
                    error_code=8000,
                    message="one of the country exists aleady with this settings",
                    country_id=country
                ), 400

        db.session.commit()
        return jsonify(
            status="OK",
            status_code=200,
            message="created tax rule",
            request_id=transaction_id
        ), 200

    else:
        if request.method == "PUT":
            count = TaxRule.query.filter_by(tax_id=tax.id).filter_by(b2c_rule=b2c).filter(TaxRule.tax_rule_uuid != arg_tax_rule_id).filter(~TaxRule.countries.any()).count()
        else:
            count = TaxRule.query.filter_by(tax_id=tax.id).filter_by(b2c_rule=b2c).filter(
                ~TaxRule.countries.any()).count()

        if count == 0:
            app.logger.info(f"no other rule with b2c={b2c} for tax {tax.id} - going to save")

            if request.method == "PUT":
                given_tax_rule.value = post_data["value"]
                given_tax_rule.tax_rule_name = post_data["rule_name"]
                given_tax_rule.b2c_rule = b2c

                db.session.add(given_tax_rule)

                for country in given_tax_rule.countries:
                    db.session.delete(country)

                given_tax_rule.countries = []
                db.session.commit()
            else:
                tax_rule = TaxRule(tax.id, post_data["value"], post_data["rule_name"], b2c)
                db.session.add(tax_rule)
                db.session.commit()
            return jsonify(
                status="OK",
                status_code=200,
                message="created tax rule",
                request_id=transaction_id
            ), 200
        else:
            app.logger.info("there is already a rule")
            return jsonify(
                status="ERROR",
                status_code=400,
                error_code=9000,
                request_id=transaction_id
            ), 400


@pluto.route('/delete/<tax_id>/<company_id>', methods=['DELETE'])
def delete_tax(tax_id, company_id):
    transaction_id = request.headers.get("x-transactionid", "")
    if not transaction_id:
        app.logger.info("no transaction id header present")
        transaction_id = str(uuid.uuid4())

    app.logger.info(f"{transaction_id}: got new transaction to create tax")

    if "x-user-id" not in request.headers or "x-user-uuid" not in request.headers:
        app.logger.info(f"{transaction_id}: user id and user uuid header not present")
        return jsonify(
            status="ERROR",
            message="please send your user as header",
            request_id=transaction_id,
            status_code=400
        ), 400

    user_id = request.headers.get("x-user-id")
    user_uuid = request.headers.get("x-user-uuid")

    validation = _validate_request(user_uuid, company_id, transaction_id)

    app.logger.info(validation)
    if validation:
        return validation

    tax = Tax.query.filter_by(tax_uuid=tax_id).filter_by(company_id=company_id).first_or_404()

    for rule in tax.tax_rules:
        for country in rule.countries:
            db.session.delete(country)
        db.session.delete(rule)
    db.session.delete(tax)
    db.session.commit()

    return jsonify(
        status="OK",
        message="successfully deleted the tax and its groups",
        status_code=200,
        request_id=transaction_id
    )


@pluto.route('/delete/taxgroup/<tax_id>/<tax_group_id>/<company_id>', methods=['DELETE'])
def delete_tax_group(tax_id, tax_group_id, company_id):
    transaction_id = request.headers.get("x-transactionid", "")
    if not transaction_id:
        app.logger.info("no transaction id header present")
        transaction_id = str(uuid.uuid4())

    app.logger.info(f"{transaction_id}: got new transaction to create tax")

    if "x-user-id" not in request.headers or "x-user-uuid" not in request.headers:
        app.logger.info(f"{transaction_id}: user id and user uuid header not present")
        return jsonify(
            status="ERROR",
            message="please send your user as header",
            request_id=transaction_id,
            status_code=400
        ), 400

    user_id = request.headers.get("x-user-id")
    user_uuid = request.headers.get("x-user-uuid")

    validation = _validate_request(user_uuid, company_id, transaction_id)

    app.logger.info(validation)
    if validation:
        return validation

    tax = Tax.query.filter_by(tax_uuid=tax_id).filter_by(company_id=company_id).first_or_404()
    tax_rule = TaxRule.query.filter_by(tax_id=tax.id).filter_by(tax_rule_uuid=tax_group_id).first_or_404()

    for country in tax_rule.countries:
        db.session.delete(country)

    db.session.delete(tax_rule)
    db.session.commit()

    return jsonify(
        status="OK",
        message="successfully deleted the tax group and its groups",
        status_code=200,
        request_id=transaction_id
    )


@pluto.route("/create/<company_id>", methods=['POST'])
def create_tax(company_id):
    transaction_id = request.headers.get("x-transactionid", "")
    if not transaction_id:
        app.logger.info("no transaction id header present")
        transaction_id = str(uuid.uuid4())

    app.logger.info(f"{transaction_id}: got new transaction to create tax")

    if "x-user-id" not in request.headers or "x-user-uuid" not in request.headers:
        app.logger.info(f"{transaction_id}: user id and user uuid header not present")
        return jsonify(
            status="ERROR",
            message="please send your user as header",
            request_id=transaction_id,
            status_code=400
        ), 400

    user_id = request.headers.get("x-user-id")
    user_uuid = request.headers.get("x-user-uuid")

    validation = _validate_request(user_uuid, company_id, transaction_id)

    app.logger.info(validation)
    if validation:
        return validation

    if not request.is_json and not request.json:
        app.logger.info(f"{transaction_id}: no json data submitted")
        return jsonify(
            status="ERROR",
            message="you have to submit a valid post json body",
            request_id=transaction_id,
            status_code=400
        ), 400
    if "tax_name" in request.json and "default_tax" in request.json:

        tax = Tax(company_id=company_id, name=request.json["tax_name"],
                  default_tax=request.json["default_tax"])
        db.session.add(tax)
        db.session.commit()

        return jsonify(
            status="OK",
            status_code=200,
            message="succesfully created tax with uuid " + tax.tax_uuid,
            request_id=transaction_id,
            tax_id=tax.tax_uuid
        ), 200

    return jsonify(
        status="ERROR",
        status_code=400,
        message="please submit valid post data",
        request_id=transaction_id
    ), 400


@pluto.route("/edit/<company_id>/<tax_id>", methods=['POST'])
def edit_tax(company_id, tax_id):
    transaction_id = request.headers.get("x-transactionid", "")
    if not transaction_id:
        app.logger.info("no transaction id header present")
        transaction_id = str(uuid.uuid4())

    app.logger.info(f"{transaction_id}: got new transaction to edit tax")

    if "x-user-id" not in request.headers or "x-user-uuid" not in request.headers:
        app.logger.info(f"{transaction_id}: user id and user uuid header not present")
        return jsonify(
            status="ERROR",
            message="please send your user as header",
            request_id=transaction_id,
            status_code=400
        ), 400

    user_id = request.headers.get("x-user-id")
    user_uuid = request.headers.get("x-user-uuid")

    validation = _validate_request(user_uuid, company_id, transaction_id)

    app.logger.info(validation)
    if validation:
        return validation

    if not request.is_json and not request.json:
        app.logger.info(f"{transaction_id}: no json data submitted")
        return jsonify(
            status="ERROR",
            message="you have to submit a valid post json body",
            request_id=transaction_id,
            status_code=400
        ), 400

    tax = Tax.query.filter_by(tax_uuid=tax_id).filter_by(company_id=company_id).first_or_404()

    if "tax_name" in request.json and "default_tax" in request.json:

        tax.name = request.json["tax_name"]
        tax.default_tax = request.json["default_tax"]
        db.session.add(tax)
        db.session.commit()

        return jsonify(
            status="OK",
            status_code=200,
            message="succesfully updated tax with uuid " + tax.tax_uuid,
            request_id=transaction_id
        ), 200

    return jsonify(
        status="ERROR",
        status_code=400,
        message="please submit valid post data",
        request_id=transaction_id
    ), 400




