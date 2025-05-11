import glob
import csv
import json
import traceback
from datetime import datetime
from elasticsearch import Elasticsearch
from elasticsearch import helpers

from elastic.hand_matching import hand_matches
from elastic.item_match import Matcher

username = 'b4aPKf8kQv'
password = 'Ci5LPNU4sJRXFBxnHj'
url = 'https://dateame-4602262096.us-east-1.bonsaisearch.net'


class Loader:
    __dataPath = None
    __es = None
    __matcher = None

    __matched = 0

    def __init__(self, path):
        self.__dataPath = path
        self.__es = Elasticsearch([url], http_auth=(username, password))
        print(self.__es.info())

        # Recreating the index..
        # ignore 400 cause by IndexAlreadyExistsException when creating an index
        self.__es.indices.delete(index='products', ignore=[400, 404])
        self.__es.indices.create(index='products', ignore=400)

        self.__matcher = Matcher()

    def run(self):

        product_code = 0

        files = glob.glob(self.__dataPath + '/*.csv')
        fields = ('url', 'provider', 'name', 'brand', 'amount_sold',
                  'amount_available', 'currency', 'pvp', 'pvp_internet',
                  'pvp_discount', 'category', 'model', 'img')

        for file in files:
            print("Reading file: {}".format(file))

            with open(file, 'r', encoding="utf-8-sig") as oFile:
                reader = csv.DictReader(oFile, fieldnames=fields, delimiter='|')
                data = [row for row in reader]
                data.pop(0)

                json_data = json.loads(json.dumps(data))

            data_to_send = []

            for line in json_data:
                data_post = {}

                # if line['category'] not in ["smartphones", "computacion", "camaras", "tablets"]:
                #     continue

                if line['pvp'] == "pvp" or line['pvp'] is None or line['pvp'] == "S/" or line['pvp_internet'] == 'Otros':
                    continue

                n = line['name'].lower()
                if "cargador" in n or "carcasa" in n or "cable" in n or "adaptador" in n or "case " in n or "trípode" in n \
                        or "funda" in n or "estuche" in n or "soporte" in n or "navaja" in n or "reloj" in n or "lentes" in n \
                        or "mochila" in n or "audífonos" in n or "parlante " in n or "protector" in n or "soporte" in n \
                        or "selfie" in n or "magsafe" in n or "mouse" in n or "teclado" in n:
                    continue

                try:
                    pvp = line['pvp'].replace(",", "")
                    pvp = 100000000 if pvp is None or pvp == "None" or pvp == "" else pvp

                    pvp_internet = line['pvp_internet'].replace(",", "")
                    pvp_internet = 1000000000 if pvp_internet is None or pvp_internet == "None" or pvp_internet == "" else pvp_internet

                    pvp_discount = line['pvp_discount'].replace(",", "")
                    pvp_discount = 1000000000 if pvp_discount is None or pvp_discount == "None" or pvp_discount == "" else pvp_discount

                    data_post['name'] = line['name']
                    data_post['category'] = line['category']
                    data_post['price'] = min(float(pvp), float(pvp_discount), float(pvp_internet))
                    data_post['url'] = line['url']
                    data_post['image'] = line['img']
                    data_post['provider'] = line['provider']
                    data_post['provider_image'] = self.get_data_provider(line['provider'])

                    data_post['product_code'] = self.__matcher.match(line)

                    if data_post['product_code'] >= 100000:
                        self.__matched += 1
                    else:
                        continue

                except Exception as e:
                    print(product_code)
                    print(line)
                    print(traceback.format_exc())
                    continue

                product_code += 1
                data_to_send.append(data_post)

            self.save(data_to_send)

            print("Products loaded: {}".format(len(data_to_send)))

        print("==> Load complete - total files: {}".format(len(files)))

    # Sending to elasticsearch
    def save(self, data):
        actions = [
            {
                "_index": "products",
                "_type": "app",
                # "_id": item["product_code"],
                "_source": {
                    "product_code": item["product_code"],
                    "name": item["name"],
                    "price": item["price"],
                    "url": item["url"],
                    "category": item["category"],
                    "image": item["image"],
                    "provider": item["provider"],
                    "provider_image": item["provider_image"]
                }
            }
            for item in data
        ]

        to_be_matched = 0
        for k, v in hand_matches.items():
            to_be_matched += len(set(v))

        print("Matched {} items from {}".format(self.__matched, to_be_matched))

        print(helpers.bulk(self.__es, actions))

    @staticmethod
    def get_data_provider(provider):

        if provider == 'MercadoLibre':
            return 'mercadolibre.png'

        elif provider == 'Sagafalabella':
            return 'sagafalabella.png'

        elif provider == 'PlazaVea':
            return 'plazavea.png'

        elif provider == 'Ripley':
            return 'ripley.png'

        elif provider == 'UnaLuka':
            return 'unaluka.png'

        if provider == 'Tottus':
            image = 'tottus.png'

        return image


current_date = datetime.now().strftime('%Y%m%d')
Loader('/home/ktodorov/projects/scrapy/data').run()
