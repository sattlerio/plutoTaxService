from app import db
import uuid


class Tax(db.Model):
    __tablename__ = "accounting_taxes"

    id = db.Column(db.Integer, primary_key=True)

    company_id = db.Column(db.String(250), nullable=False)
    tax_uuid = db.Column(db.String(250), unique=True, nullable=False)
    name = db.Column(db.String(250), nullable=False)
    default_tax = db.Column(db.Numeric, nullable=False, default=0.00)

    tax_rules = db.relationship("TaxRule", backref="accounting_taxes", lazy=True, cascade='delete,all')

    def __init__(self, company_id, name, default_tax):
        self.company_id = company_id
        self.name = name
        self.tax_uuid = uuid.uuid4().hex
        self.default_tax = default_tax


class TaxRule(db.Model):
    __tablename__ = "accounting_tax_rules"

    id = db.Column(db.Integer, primary_key=True)

    tax_rule_name = db.Column(db.String(250), nullable=False)
    tax_rule_uuid = db.Column(db.String(250), unique=True, nullable=False)

    tax_id = db.Column(db.Integer, db.ForeignKey("accounting_taxes.id"), nullable=False)

    value = db.Column(db.Numeric, nullable=False, default=0.00)

    b2c_rule = db.Column(db.Boolean, default=False, nullable=False)

    countries = db.relationship("TaxRuleCountry", backref="accounting_tax_rules", cascade='delete,all', lazy=True)

    def __init__(self, tax_id, value, tax_rule_name, b2c_rule=False):
        self.value = value
        self.tax_rule_name = tax_rule_name
        self.tax_id = tax_id
        self.tax_rule_uuid = uuid.uuid4().hex
        self.b2c_rule = b2c_rule


class TaxRuleCountry(db.Model):
    __tablename__ = "rel_accounting_tax_rule_2_countries"

    id = db.Column(db.Integer, primary_key=True)

    tax_rule_id = db.Column(db.Integer, db.ForeignKey("accounting_tax_rules.id"), nullable=False)
    country_id = db.Column(db.String(3), nullable=False)

    def __init__(self, country_id):
        self.country_id = country_id
