import os
import datetime
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    DEBUG = False
    TESTING = False
    CSRF_ENABLED = True
    SECRET_KEY = 'this-really-needs-to-be-changed'
    BUILD_NUMBER = "##BUILD_NUMBER##"
    BUILD_ID = "##BUILD_ID##"
    BUILD_TAG = "##BUILD_TAG##"
    GIT_COMMIT = "##GIT_COMMIT##"
    JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(days=0, hours=4)

    GUARDIAN_SERVICE = os.environ.get("GUARDIAN_SERVICE_URL")
    GEOSERVICE = os.environ.get("GEOSERVICE_URL")


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')


class StagingConfig(Config):
    DEVELOPMENT = True
    DEBUG = True


class DevelopmentConfig(Config):
    DEVELOPMENT = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres:d0nt4get@localhost/pluto"
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    GUARDIAN_SERVICE = "http://localhost:8080/resources/authorization/permission"
    GEOSERVICE = "http://localhost:8080/resources/geo/countries"


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test.db'