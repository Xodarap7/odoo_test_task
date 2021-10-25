from configparser import ConfigParser
import sys
import requests


config = ConfigParser()
config.read(str(sys.argv[1]))


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
        self.remote_source = config.get('remote_system', 'source')
        self.remote_receiver = config.get('remote_system', 'receiver')

        remote_systems = {'source': None, 'receiver': None}

        if self.remote_source == 'swapi':
            swapi_source = SwapiSource()
            swapi_source.read_config()
            remote_systems['source'] = swapi_source

        if self.remote_receiver == 'odoo':
            odoo_receiver = OdooReceiver()
            odoo_receiver.read_config()
            remote_systems['receiver'] = odoo_receiver

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
        # print(content)
        return content

    def get_swapi_id(self, content_url):

        """
        Function getting id from url of contents
        :return: element id
        """

        elem_id = content_url.split('/')[-2]
        return elem_id


class OdooReceiver:
    def __init__(self):
        self.url = None
        self.db = None
        self.username = None
        self.password = None

    def read_config(self):
        self.url = config.get('odoo', 'url')
        self.db = config.get('odoo', 'db')
        self.username = config.get('odoo', 'username')
        self.password = config.get('odoo', 'password')

class Planets:
    def __init__(self, name, diameter, rotation_period, orbital_period, population):
        self.name = name
        self.diameter= diameter
        self.rotation_period = rotation_period
        self.orbital_period = orbital_period
        self.population = population
    def push_data(self):
        pass

class Contacts:
    def __init__(self, name, planet, photo):
        self.name = name
        self.planet = planet
        self.photo = photo