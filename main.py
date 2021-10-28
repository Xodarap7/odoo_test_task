import classes

configurer = classes.Configurer()   # getting configuration
systems = configurer.set_config()   # getting source system ang receiver system

source = systems['source']
receiver = systems['receiver']

entities = configurer.select_etities()  # getting entities for transfer

entity_objects = source.create_objects(source, entities)    # entity objects
planets = entity_objects['planets']
contacts = entity_objects['contacts']

receiver.get_connect()

for contact in contacts:
    contact.push_data(receiver, planets)    # starts transfer to receiver


