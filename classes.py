from configparser import ConfigParser
import sys
import requests
import xmlrpc.client
import logging
import base64

config = ConfigParser()
config.read(str(sys.argv[1]))


def init_logger(name):
    """
    Create logger configuration
    """
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
logger = logging.getLogger('app.classes')


class Configurer:
    """
    read config and create instance of source and receiver
    """
    def __init__(self):
        self.remote_source = None
        self.remote_receiver = None

    def set_config(self):
        """
        create source and receiver
        :return:
        dict of instances
        """
        logger.info("Install config")
        self.remote_source = config.get('remote_system', 'source')
        self.remote_receiver = config.get('remote_system', 'receiver')

        remote_systems = {'source': None, 'receiver': None}

        if self.remote_source == 'swapi':
            swapi_source = SwapiSource()
            swapi_source.read_config()
            remote_systems['source'] = swapi_source
            logger.info("source=swapi")

        if self.remote_receiver == 'odoo':
            odoo_receiver = OdooReceiver()
            odoo_receiver.read_config()
            remote_systems['receiver'] = odoo_receiver
            logger.info("receiver=odoo")

        return remote_systems

    def select_etities(self):
        """
        get a list of entities
        :return:
        entities
        """
        entities = config.get('entities', 'entities').split(', ')
        return entities


class SwapiSource:
    """
    class that receives data from "Swapi" and creates objects of entity classes
    """
    def __init__(self):
        self.planetsUrl = None
        self.contactsUrl = None
        self.photosUrl = None
        self.urls = None

    def read_config(self):
        """
        get urls from config
        """
        self.planetsUrl = config.get('swapi', 'planetsUrl')
        self.contactsUrl = config.get('swapi', 'contactsUrl')
        self.photosUrl = config.get('swapi', 'photosUrl')
        self.urls = {'planets': self.planetsUrl, 'contacts': self.contactsUrl}

    def get_content(self, content_url):
        """
        get content from all url
        :param content_url: url of certain content
        :return:
        certain content
        """
        response = requests.get(content_url)
        page = response.json()
        content = page['results']
        while page['next'] is not None:
            content_url = page['next']
            response = requests.get(content_url)
            page = response.json()
            content += page['results']
        return content

    def create_objects(self, source, entities):
        """
        creates objects of entity classes
        :param source: source of data
        :param entities: entities for transfer

        :return: dict with entity objects
        {entity1: entity1_objects, entity2: entity2_objects}
        """
        logger.info("Receiving data")
        planets = []
        contacts = []
        entity_objects = {}
        try:
            for entity in entities:
                url = source.urls.get(entity)
                content = source.get_content(url)
                if entity == "planets":
                    logger.info("Receiving planets")
                    for planet in content:
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
                        new_planet = Planets(
                            planet['name'],
                            planet['diameter'],
                            planet['rotation_period'],
                            planet['orbital_period'],
                            population)
                        new_planet.source_id = source.get_source_id(planet['url'])
                        planets.append(new_planet)
                    entity_objects['planets'] = planets

                elif entity == "contacts":
                    logger.info("Receiving contacts")
                    for contact in content:
                        planet_id = source.get_source_id(contact['homeworld'])
                        people_id = source.get_source_id(contact['url'])
                        homeworld = ""
                        for planet in planets:
                            if planet.source_id == planet_id:
                                homeworld = planet.name
                        photo_url = f'{source.photosUrl}{people_id}.jpg'
                        new_contact = Contacts(
                            contact['name'],
                            homeworld,
                            photo_url)
                        new_contact.source_id = people_id
                        contacts.append(new_contact)
                    entity_objects['contacts'] = contacts
        except Exception as e:
            logger.error(e)
        finally:
            return entity_objects

    def get_source_id(self, content_url):

        """
        Function getting id from url of contents
        :return: element id
        """

        elem_id = content_url.split('/')[-2]
        return elem_id


class OdooReceiver:
    """
    entity transfer management class
    """
    def __init__(self):
        self.url = None
        self.db = None
        self.username = None
        self.password = None
        self.uid = None
        self.models = None

    def read_config(self):
        self.url = config.get('odoo', 'url')
        self.db = config.get('odoo', 'db')
        self.username = config.get('odoo', 'username')
        self.password = config.get('odoo', 'password')

    def get_connect(self):
        """
        establishing a connection with receiver
        """
        try:
            logger.info('Connecting to Odoo')
            common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(self.url))
            self.uid = common.authenticate(self.db, self.username, self.password, {})
            self.models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(self.url))
        except:
            logger.error('Failed to connect to db')
        else:
            logger.info('Connection with Odoo established successfully')

    def search_by_name(self, model, content):
        """
        item search in odoo
        :param model: odoo model ('res.partner')
        :param content:
        :return: required element
        """
        elem = self.models.execute_kw(
            self.db, self.uid, self.password,
            model, 'search',
            [[['name', '=', content.name]]])[0]
        return elem

    def push_content(self, entity, elem, img='', planet=''):
        """
        Function for push element to odoo
        :param entity: element entity
        :param elem: element to carry
        :param img: url of image (optional)
        :param planet: name planet (optional)
        :return: 'receiver id' for further transfer of contacts or logging
        """
        receiver_id = None
        if entity == 'contact':
            receiver_id = self.models.execute_kw(self.db, self.uid, self.password, 'res.partner', 'create', [{
                'company_type': 'person',
                'name': elem.name,
                'planet': planet,
                'image_1920': img}])
        elif entity == 'planet':
             receiver_id = self.models.execute_kw(self.db, self.uid, self.password, 'res.planet', 'create', [{
                'name': elem.name,
                'diameter': elem.diameter,
                'rotation_period': elem.rotation_period,
                'orbital_period': elem.orbital_period,
                'population': elem.population}])
        return receiver_id


class Planets:
    """
    entity Planet
    """
    def __init__(self, name, diameter, rotation_period, orbital_period, population):
        self.source_id = None
        self.receiver_id = None
        self.name = name
        self.diameter = diameter
        self.rotation_period = rotation_period
        self.orbital_period = orbital_period
        self.population = population

    def push_data(self, receiver):
        """
        function starts transferring the object
        :param receiver: into which system is the transfer
        :return:'receiver id' for further transfer of contacts or logging
        """
        try:
            """Check planet in odoo"""
            self.receiver_id = receiver.search_by_name('res.planet', self)
        except:
            """adding planet"""
            try:
                self.receiver_id = receiver.push_content('planet', self)
            except:
                logger.error(f"Error while adding planet {self.name}")
            else:
                logger.info(f'Successfully added: Planet {self.name},'
                            f' remote system ID=[{self.source_id}], Odoo ID=[{self.receiver_id}]')
        else:
            logger.info(f'Planet {self.name} already exists')
        finally:
            return self.receiver_id


class Contacts:
    """
    entity contact
    """
    def __init__(self, name, planet, photo_url):
        self.source_id = None
        self.receiver_id = None
        self.name = name
        self.planet = planet
        self.photo_url = photo_url

    def push_data(self, receiver, planets):
        """
        function starts transferring the object
        :param receiver: into which system is the transfer
        :param planets: list of planets
        """
        try:
            try:
                """Check contact in odoo"""
                self.receiver_id = receiver.search_by_name('res.partner', self)
            except:
                planet_id = None
                for planet in planets:
                    if planet.name == self.planet:
                        try:
                            planet_id = planet.push_data(receiver)
                        except Exception as e:
                            print(e)
                img = requests.get(self.photo_url)
                img = base64.b64encode(img.content).decode('utf-8')
                try:
                    self.receiver_id = receiver.push_content('contact', self, img, planet_id)
                except:
                    logger.error('Error while adding contact')
                else:
                    logger.info(f'Successfully added: Contact {self.name},'
                                f' remote system ID=[{self.source_id}], Odoo ID=[{self.receiver_id}]')
            else:
                logger.error(f'Contact {self.name} already exists')
        except Exception as e:
            logger.error(e)
