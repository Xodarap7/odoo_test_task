from configparser import ConfigParser
import sys
import requests
import base64
import xmlrpc.client
import logging

# Getting path of Config file
config = ConfigParser()
config.read(str(sys.argv[1]))

# Getting parameters from config.ini
url = config.get('odoo', 'url')
db = config.get('odoo', 'db')
username = config.get('odoo', 'username')
password = config.get('odoo', 'password')


# Function for create logger (console log and file log)
def init_logger(name):
    logger = logging.getLogger(name)
    FORMAT = '%(levelname)s :: %(asctime)s :: %(name)s:%(lineno)s :: %(message)s'
    logger.setLevel(logging.INFO)
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter(FORMAT))
    sh.setLevel(logging.INFO)
    fh = logging.FileHandler(filename='logs/test.log')
    fh.setFormatter(logging.Formatter(FORMAT))
    fh.setLevel(logging.INFO)
    logger.addHandler(sh)
    logger.addHandler(fh)


init_logger('app')
logger = logging.getLogger('app.main')


# Function getting content from all pages on url
# return list of "contents"
def get_content(content_url):
    response = requests.get(content_url)
    page = response.json()
    content = page['results']
    while page['next'] is not None:
        content_url = page['next']
        response = requests.get(content_url)
        page = response.json()
        content += page['results']
    return content


# Function getting id from url of contents
# return id
def get_swapi_id(content_url):
    elem_id = content_url.split('/')[-2]
    return elem_id


# Function found elements in odoo
# return id of odoo elements
def search_by_name(model, content):
    elem = models.execute_kw(
        db, uid, password,
        model, 'search',
        [[['name', '=', content['name']]]])[0]
    return elem


# Function for adding planets in odoo

# What is function doing:
# 1. Gets a list of planets to add
# 2. Сhecks for every a new planet in Odoo
# 3. If the planet does not exist then add it
# 4. If the planet exists then does not add it
#
# Inaccuracies:
#   If population out of range "int" (>2147483640), then this is a mistake, but population in Odoo is float.
# If i change type in Odoo to String, i still get the same error.
# Example: adding_planets('swapi', 'planetsUrl', planets_model)

def adding_planets(config_section, config_property, model):
    logger.info('The process of transferring the planets has begun')
    logger.info("Getting planets and planet's data")
    planets = get_content(config.get(config_section, config_property))  # 1
    logger.info(f'{str(len(planets))} planets received')
    logger.info('Started adding planets to Odoo')
    for planet in planets:
        try:
            search_by_name(model, planet)   # 2
        except:
            if planet['population'] == 'unknown':
                planet['population'] = '0'
            if planet['rotation_period'] == 'unknown':
                planet['rotation_period'] = '0'
            if planet['orbital_period'] == 'unknown':
                planet['orbital_period'] = '0'
            if planet['diameter'] == 'unknown':
                planet['diameter'] = '0'
            population = float(planet['population'])
            if population > 2147483640:
                population = float(str(population).replace(str(population), '999999999'))
            try:
                planet['id'] = get_swapi_id(planet['url'])
                models.execute_kw(db, uid, password, model, 'create', [{    # 3
                    'name': planet['name'],
                    'diameter': planet['diameter'],
                    'rotation_period': planet['rotation_period'],
                    'orbital_period': planet['orbital_period'],
                    'population': population}])
                odoo_id = search_by_name(model, planet)
                logger.info(f'Successfully added: Planet {planet["name"]},'
                            f' remote system ID=[{planet["id"]}], Odoo ID=[{odoo_id}]')
            except Exception as e:
                logger.error(e)
        else:                                                           # 4
            logger.error(f'Planet {planet["name"]} already exists')
    logger.info('Adding planets completed')


# Function for adding contacts in odoo

# What is function doing:
# 1. Gets a list of contacts to add
# 2. Сhecks for every a new contact in Odoo
# 3. If the contact does not exist then add it
# 4. If contacts added successful, then add photo fot it
# 5. If the contact exists then does not add it
#
# example: adding_partners('swapi', 'peoplesUrl', 'photosUrl', partners_model)

def adding_partners(config_section, config_property_partners, config_property_photos, model):
    logger.info('The process of transferring the peoples has begun')
    logger.info("Getting contacts and contact's data")
    peoples = get_content(config.get(config_section, config_property_partners))
    logger.info(f'{len(peoples)} contacts received')
    logger.info('Started adding contacts to Odoo')
    for people in peoples:
        try:
            search_by_name(model, people)
        except:
            try:
                people['id'] = get_swapi_id(people['url'])
                planet_id = get_swapi_id(people['homeworld'])
                res = requests.get(f'{config.get("swapi", "planetsUrl")}{planet_id}/')
                planet = res.json()

                planet_odoo_id = search_by_name('res.planet', planet)

                models.execute_kw(db, uid, password, model, 'create', [{
                    'company_type': 'person',
                    'name': people['name'],
                    'planet': planet_odoo_id}])
                odoo_id = search_by_name(model, people)
                logger.info(f'Successfully added: Contact {people["name"]},'
                            f' remote system ID=[{people["id"]}], Odoo ID=[{odoo_id}]')
            except Exception as e:
                logger.error(e)
            else:
                try:
                    img = requests.get(f'{config.get(config_section, config_property_photos)}{people["id"]}.jpg')
                    img = base64.b64encode(img.content).decode('utf-8')
                    people_odoo_id = search_by_name(model, people)

                    models.execute_kw(
                        db, uid, password,
                        model, 'write',
                        [[people_odoo_id], {'image_1920': img}])
                    logger.info(f'Successfully added: Contact {people["name"]} photo added')
                except:
                    logger.warning(f'Error adding photo: people {people["name"]}')
        else:
            logger.error(f'Contact {people["name"]} already exists')
    logger.info('Adding contacts completed')


# Odoo connection parameters
try:
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, username, password, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
except:
    logger.error('Failed to connect to db')
else:
    logger.info('Connection with Odoo established successfully')
    adding_planets('swapi', 'planetsUrl', 'res.planet')
    adding_partners('swapi', 'peoplesUrl', 'photosUrl', 'res.partner')
