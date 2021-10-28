import classes
import time


def slice_content(content, max_len):
    """
    function slice content list into small blocks
    :param content: content list
    :param max_len: block size
    :return: list with blocks
    """
    lists_content = []
    while len(content) > 0:
        block = []
        block += content[-max_len:]
        del content[-max_len:]
        lists_content.append(block)
    return lists_content


configurer = classes.Configurer()   # getting configuration
systems = configurer.set_config()   # getting source system ang receiver system

source = systems['source']
receiver = systems['receiver']

entities = configurer.select_etities()  # getting entities for transfer

entity_objects = source.create_objects(source, entities)    # entity objects
planets = entity_objects['planets']
contacts = entity_objects['contacts']
receiver.get_connect()

if len(contacts) > 1000:    # starts transfer to receiver
    lists_contacts = slice_content(contacts, 1000)
    for contacts in lists_contacts:
        time.sleep(0)
        for contact in contacts:
            contact.push_data(receiver, planets)
else:
    for contact in contacts:
        contact.push_data(receiver, planets)





