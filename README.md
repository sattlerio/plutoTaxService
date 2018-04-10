hades Authentication Service
----------
Pluto is a Microservice Service using JWT to Login users. As Database it uses any RDBMS (in production it uses PostgreSQL)

----------

Local Development
-------------
To work with the runbot locally you can use docker or your local host.

1. Checkout the project locally
2. Create virtualenvironment and install dependencies

    (in project directory): $ virtualenv -p python3 venv
    (in project directory): $ . venv/bin/activate
    (in project directory): $ pip install -r requirements/base.txt
    
3. 