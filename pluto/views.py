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


@pluto.route("/<tax_id>/create/rule/<company_id>", methods=["POST"])
def add_rule_to_tax(tax_id, company_id):
    transaction_id = request.headers.get("x-transactionid", "")
    if not transaction_id:
        app.logger.info("no transaction id header present")
        transaction_id = str(uuid.uuid4())

    app.logger.info(f"{transaction_id}: got new transaction to create rule for tax")

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

    post_data = request.json
    if not post_data or "countries" not in post_data:
        app.logger.info("countries not present in post data")
        return jsonify(
            status="ERROR",
            message="please submit valid POST body",
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

    countries = post_data["countries"]
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

    if "b2c" in post_data:
        if post_data["b2c"]:
            b2c =  True
        else:
            b2c = False
    else:
        b2c = False

    tax_rule = TaxRule(tax.id, b2c)

    for country in validated_countries:
        tax_rule.countries.append(TaxRuleCountry(country_id=country))

    db.session.add(tax_rule)
    db.session.commit()

    return jsonify(
        status="OK",
        status_code=200,
        message="created tax rule",
        request_id=transaction_id
    ), 200


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
            request_id=transaction_id
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




