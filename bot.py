#!/usr/bin/env python3

from PIL import Image
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from random import choice
import requests
import smtplib


API_PREFIX = "https://beta.interieur.gouv.fr/candilib/api/v2/"
# API_PREFIX = "https://candilib.ynerant.fr/candilib/api/v2/"
# API_PREFIX = "http://localhost/candilib/api/v2/"

CAPTCHA_IMAGES = {
    "L'avion": "airplane",
    "Les ballons": "balloons",
    "L'appareil photo": "camera",
    "La Voiture": "car",
    "Le chat": "cat",
    "La chaise": "chair",
    "Le trombone": "clip",
    "L'horloge": "clock",
    "Le nuage": "cloud",
    "L'ordinateur": "computer",
    "L'enveloppe": "envelope",
    "L'oeil": "eye",
    "Le drapeau": "flag",
    "Le dossier": "folder",
    "Le pied": "foot",
    "Le graphique": "graph",
    "La maison": "house",
    "La clef": "key",
    "La feuille": "leaf",
    "L'ampoule": "light-bulb",
    "Le cadenas": "lock",
    "La loupe": "magnifying-glass",
    "L'homme": "man",
    "La note de musique": "music-note",
    "Le pantalon": "pants",
    "Le crayon": "pencil",
    "L'imprimante": "printer",
    "Le robot": "robot",
    "Les ciseaux": "scissors",
    "Les lunettes de soleil": "sunglasses",
    "L'étiquette": "tag",
    "L'arbre": "tree",
    "Le camion": "truck",
    "Le T-Shirt": "t-shirt",
    "Le parapluie": "umbrella",
    "La femme": "woman",
    "La planète": "world"
}


def calculate_checksums():
    for name in CAPTCHA_IMAGES.values():
        img = Image.open(f'captcha_images/{name}.png')
        img.save(f'captcha_images/{name}.ppm')
        with open(f'captcha_images/{name}.ppm', 'rb') as f:
            with open(f'captcha_images/{name}.ppm.sum', 'w') as f_sum:
                f_sum.write(hashlib.sha512(f.read()).hexdigest())


@dataclass
class Candidat:
    codeNeph: str = ''
    homeDepartement: str = ''
    departement: str = '75'
    email: str = ''
    nomNaissance: str = ''
    prenom: str = ''
    portable: str = ''
    adresse: str = ''
    visibilityHour: str = '12H50'
    dateETG: str = ''
    isInRecentlyDept: bool = False


@dataclass
class Places:
    _id: str = ''
    centre: "Centre" = None
    date: str = ''
    lastDateToCancel: str = ''
    canBookFrom: str = ''
    timeOutToRetry: int = 0
    dayToForbidCancel: int = 7
    visibilityHour: str = '12H50'


@dataclass(order=True)
class Departement:
    geoDepartement: str = ''
    centres: list["Centre"] = None
    count: int = None


@dataclass
class Centre:
    _id: str
    count: int = 0
    longitude: float = 0.0
    latitude: float = 0.0
    nom: str = ""
    departement: Departement = None
   

def api(path: str, token: str, user_id: str, app: str = 'candidat', **kwargs) -> dict:
    return requests.get(
            API_PREFIX + app + '/' + path,
            data=kwargs,
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
                'X-USER-ID': user_id,
            },
        ).json()


def send_mail(content: str, subject: str) -> None:
    print('\n')
    print(subject)
    print(len(subject) * '-')
    print()
    return print(content)
    smtp = smtplib.SMTP('localhost', 25)
    content = f"""From: Ÿnérant <ynerant@crans.org>
To: Ÿnérant <ynerant+candilib@crans.org>
Subject: {subject}

""" + content
    content = content.encode('UTF-8')
    smtp.sendmail('ynerant@crans.org', ['ynerant+candilib@crans.org'], content)


def main(token: str) -> None:
    response = requests.get(API_PREFIX + 'auth/candidat/verify-token?token=' + token)
    try:
        assert response.json()['auth']
    except (AssertionError, KeyError):
        raise ValueError(f"Une erreur est survenue lors de la connexion : {response.content.decode('utf-8')}")
    user_id = response.headers['X-USER-ID']

    me = Candidat(**api('me', token, user_id)['candidat'])
    print(f'Salut {me.prenom} {me.nomNaissance} !')


    departements = [Departement(**dpt) for dpt in api('departements', token, user_id)['geoDepartementsInfos']]
    departements.sort()

    for dpt in departements:
        centres = api(f'centres?departement={dpt.geoDepartement}&end=2021-07-31T23:59:59.999', token, user_id)
        dpt.centres = []
        dpt.count = 0
        for centre in centres:
            centre = Centre(
                     _id=centre['centre']['_id'],
                     nom=centre['centre']['nom'],
                     count=centre['count'],
                     longitude=centre['centre']['geoloc']['coordinates'][0],
                     latitude=centre['centre']['geoloc']['coordinates'][1],
                     departement=dpt,
            )
            dpt.centres.append(centre)
            dpt.count += centre.count

    places = Places(**api('places', token, user_id))
    if places.centre:
        for dpt in departements:
            for centre in dpt.centres:
                if centre._id == places.centre['_id']:
                    places.centre = centre
                    break
            else:
                continue
            break

    if places.date:
        print(f"Vous avez déjà une date d'examen, le {places.date}.")
        exit(1)

    print("\n")
    for dpt in departements:
        print(dpt.geoDepartement, dpt.count)

    for dpt in departements:
        for centre in dpt.centres:
            dates = api(f"places?begin=2021-04-26T00:00:00.000&end=2021-07-31T23:59:59.999+02:00&geoDepartement={dpt.geoDepartement}&nomCentre={centre.nom}", token, user_id)
            send_mail(json.dumps(dates, indent=2), centre.nom)
            centre.dates = dates

    PREFERRED_CENTRES = ["MASSY", "ANTONY", "RUNGIS", "MONTGERON", "CLAMART", "SAINT CLOUD", "EVRY",
                         "VILLABE", "ETAMPES", "VELIZY VILLACOUBLAY", "MAISONS ALFORT", "TRAPPES", "SAINT PRIEST"]

    for name in PREFERRED_CENTRES:
        for dpt in departements:
            for centre in dpt.centres:
                if centre.nom == name:
                    break
            else:
                continue
            break
        for date in centre.dates:
            if name == "SAINT PRIEST" and ("T07:" in date or "T08:" in date):
                continue
            break
        else:
            continue
        break
    else:
        print("Aucune date intéressante")
        return

    print("Centre :", centre.nom)
    print("Date :", date)
    # Resolve captcha
    captcha_info = api('verifyzone/start', token, user_id)
    print(captcha_info)
    captcha_info = captcha_info['captcha']
    field = captcha_info['imageFieldName']
    image_name = captcha_info['imageName']
    image_file = CAPTCHA_IMAGES[image_name]
    captcha_images = captcha_info['values']

    with open(f'captcha_images/{image_file}.ppm.sum') as f:
        valid_checksum = f.read().strip()

    for i in range(5):
        response = requests.get(
            f'{API_PREFIX}candidat/verifyzone/image/{i}',
            headers={
                'Accept': 'application/json',
                'Authorization': f'Bearer {token}',
                'X-USER-ID': user_id,
            },
        )
        with open(f'/tmp/image_{i}.png', 'wb') as f:
            f.write(response.content)
        img = Image.open(f'/tmp/image_{i}.png')
        img.save(f'/tmp/image_{i}.ppm')
        with open(f'/tmp/image_{i}.ppm', 'rb') as f:
            checksum = hashlib.sha512(f.read()).hexdigest()
            if checksum == valid_checksum:
                captcha_result = captcha_images[i]

    print(requests.patch(
            API_PREFIX + 'candidat/places',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
                'X-USER-ID': user_id,
            },
            json={
                'geoDepartement': centre.departement.geoDepartement,
                'nomCentre': centre.nom,
                'date': date,
                'hasDualControlCar': True,
                'isAccompanied': True,
                'isModification': False,
                field: captcha_result,
            },
    ).content)


if __name__ == '__main__':
    with open('/var/local/candibot/.token') as f:
        token = f.read().strip()
    main(token)
