from configparser import ConfigParser
import sys
import requests
import base64
import xmlrpc.client

config = ConfigParser()
config.read(str(sys.argv[1]))

url = config.get('odoo', 'url')
db = config.get('odoo', 'db')
username = config.get('odoo', 'username')
password = config.get('odoo', 'password')

partners_model = config.get('models', 'partners')
planets_model = config.get('models', 'planets')

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
common.version()
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))


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


def get_swapi_id(content_url):
    elem_id = content_url.split('/')[-2]
    return elem_id


def search_by_name(model, content):
    elem = models.execute_kw(
        db, uid, password,
        model, 'search',
        [[['name', '=', content['name']]]])[0]
    return elem


def adding_planets(config_section, config_property, model):
    planets = get_content(config.get(config_section, config_property))
    for planet in planets:
        try:
            search_by_name(model, planet)
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
                models.execute_kw(db, uid, password, model, 'create', [{
                    'name': planet['name'],
                    'diameter': planet['diameter'],
                    'rotation_period': planet['rotation_period'],
                    'orbital_period': planet['orbital_period'],
                    'population': population}])
                print('Success')
            except Exception as e:
                print(e)
        else:
            print('Planet '+planet['name']+' already exists')


def adding_partners(config_section, config_property_partners, config_property_photos, model):
    peoples = get_content(config.get(config_section, config_property_partners))
    for people in peoples:
        try:
            search_by_name(model, people)
        except:
            try:
                people['id'] = get_swapi_id(people['url'])
                planet_id = get_swapi_id(people['homeworld'])
                res = requests.get(config.get('swapi', 'planetsUrl') + planet_id + '/')
                planet = res.json()

                planet_odoo_id = search_by_name(planets_model, planet)

                models.execute_kw(db, uid, password, model, 'create', [{
                    'company_type': 'person',
                    'name': people['name'],
                    'planet': planet_odoo_id}])

                print('Success')
            except Exception as e:
                print(e)
            try:
                img = requests.get(config.get(config_section, config_property_photos) + people['id'] + '.jpg')
                img = str(base64.b64encode(img.content))[1:-1]

                people_odoo_id = search_by_name(model, people)

                models.execute_kw(
                    db, uid, password,
                    model, 'write',
                    [[people_odoo_id], {'image_1920': img}])
                print('Photo was added')
            except:
                print("huli")
        else:
            print('Contact ' + people['name'] + ' already exists')


adding_planets('swapi', 'planetsUrl', planets_model)
adding_partners('swapi', 'peoplesUrl', 'photosUrl', partners_model)

