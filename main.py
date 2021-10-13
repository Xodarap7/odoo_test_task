## How change type Integer to Str???   -- 51-53
## Не добавлять уже добавленные записи
## Сделать чтобы отсутствие какого либо значения не препятствовало добавлению записи
## Вынести конфигурационные значения в файл конфигурации
## Создать логирование и определить как определять id в оду

import requests
import odoolib
import base64

planetsUrl = "https://swapi.dev/api/planets/"
peoplesUrl = "https://swapi.dev/api/people/"
photosUrl = "https://starwars-visualguide.com/assets/img/characters/"

connection = odoolib.get_connection(
    hostname="localhost",
    database="StarWars",
    login='basyar86@gmail.com',
    password="J7UYQbGZ5iUewLA",
)


def get_content(url):
    res = requests.get(url)
    page = res.json()
    content = page["results"]
    while page["next"] is not None:
        url = page["next"]
        res = requests.get(url)
        page = res.json()
        content += page["results"]
    return content


def get_swapi_id(url):
    id = url.split("/")[-2]
    return id


peoples = get_content(peoplesUrl)
planets = get_content(planetsUrl)

planet_model = connection.get_model("res.planet")
people_model = connection.get_model("res.partner")

for planet in planets:

    if planet["population"] == "unknown":
        planet["population"] = "0"
    if planet["rotation_period"] == "unknown":
        planet["rotation_period"] = "0"
    if planet["orbital_period"] == "unknown":
        planet["orbital_period"] = "0"
    if planet["diameter"] == "unknown":
        planet["diameter"] = "0"
    population = float(planet["population"])
    if population > 2147483640:
        population = float(str(population).replace(str(population), "999999999"))
    try:
        new_planet = planet_model.create(
            dict(name=planet["name"], diameter=planet["diameter"], rotation_period=planet["rotation_period"],
                 orbital_period=planet["orbital_period"], population=population))
        planet["id"] = get_swapi_id(planet["url"])
        print("Успешно")
    except Exception as e:
        print(e)

for people in peoples:
    people["id"] = get_swapi_id(people["url"])
    planet_id = get_swapi_id(people["homeworld"])
    res = requests.get("https://swapi.dev/api/planets/"+planet_id+"/")
    planet = res.json()
    planet_odoo_id = planet_model.search([("name", "=", planet["name"])])[0]

    img = requests.get(photosUrl+people["id"]+".jpg")
    img = str(base64.b64encode(img.content))[1:-1]
    try:
        new_people = people_model.create(
            dict(company_type="person", name=people["name"], image_1920=img, planet=planet_odoo_id))
        print("Успешно")
    except Exception as e:
        print(e)
