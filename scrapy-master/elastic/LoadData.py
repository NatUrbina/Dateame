# Created by Miguel Pazo (https://miguelpazo.com)
import glob
import csv
import json
import traceback
import hashlib
import unidecode
import mysql.connector
from datetime import datetime
from elasticsearch import Elasticsearch
from elasticsearch import helpers

from common.Utils import Utils

elastic_url = 'http://35.229.125.16:9200'
elastic_username = 'apps'
elastic_password = 'b4xjXYauyNUuyq2A'

mysql_host = '35.243.203.59'
mysql_database = 'dateame'
mysql_username = 'apps'
mysql_password = 'b4xjXYauyNUuyq2A'


# mysql_host = 'localhost'
# mysql_database = 'dateame'
# mysql_username = 'root'
# mysql_password = 'root'


class LoadData:
    __data_path = None
    __data_path_out = None
    __es = None
    __index = 'products'

    def __init__(self, path, path_out):
        self.__data_path = path
        self.__data_path_out = path_out
        self.__es = Elasticsearch([elastic_url], http_auth=(elastic_username, elastic_password))

        self.run()

    def run(self):
        files = glob.glob(self.__data_path + '/*.csv')
        fields = ('url', 'provider', 'name', 'brand', 'amount_sold',
                  'amount_available', 'currency', 'pvp', 'pvp_internet',
                  'pvp_discount', 'category', 'model', 'img', 'product_id',
                  'product_code', 'vendor', 'timestamp', 'time_iso')

        # mercadolibre
        filter_vendors = ['3601594', '84683920', '144233366', '146232397']
        filter_vendors_names = {'3601594': 'beauritz', '84683920': 'wienerstech', '144233366': 'teckimports01', '146232397': 'miraflores'}
        providers_ids = ['wienerstech', 'miraflores', 'beauritz', 'electro-cyber', 'duval import', 'fortum4+store', 'amptechnology', 'enviosusaperu_ml', 'unaluka']

        all_data = []
        data_by_index = {}

        for file in files:
            print("Reading file: {}".format(file))
            file_parts = file.split('-')
            index_date = file_parts[len(file_parts) - 1].replace('.csv', '').strip()
            timestamp = datetime.strptime("{} 08:00:00".format(index_date), '%Y%m%d %H:%M:%S')

            with open(file, 'r', encoding="utf-8-sig") as filen_open:
                reader = csv.DictReader(filen_open, fieldnames=fields, delimiter='|')

                for row in reader:
                    if row['url'] != 'url' and 'http' in row['url'] and row['pvp'] is not None:
                        row['product_id'] = hashlib.sha256(row['url'].encode()).hexdigest()
                        row['provider'] = row['provider'].lower()
                        row['brand'] = row['brand'].lower()
                        row['model'] = '' if row['model'] is None else row['model'].lower()
                        row['category'] = Utils.proc_category(row['category'])
                        row['name'] = Utils.proc_name(row['name'])
                        row['timestamp'] = datetime.timestamp(timestamp) - (60 * 60 * 5)
                        row['time_iso'] = timestamp.isoformat()
                        row['product_code'] = ''

                        row['pvp'] = Utils.proc_price(row['pvp'])
                        row['pvp_internet'] = Utils.proc_price(row['pvp_internet'])
                        row['pvp_discount'] = Utils.proc_price(row['pvp_discount'])

                        row['amount_sold'] = Utils.proc_amount(row['amount_sold'])
                        row['amount_available'] = Utils.proc_amount(row['amount_available'])

                        if '-' in row['provider']:
                            provider_parts = row['provider'].split('-')
                            row['provider'] = provider_parts[0]
                            row['vendor'] = providers_ids[int(provider_parts[1]) - 1]

                        if row['provider'] in filter_vendors:
                            row['vendor'] = filter_vendors_names[row['provider']]
                            row['provider'] = 'mercadolibre'

                        if row['provider'] == 'sagafalabella_smartphones' or row['provider'] == 'trust':
                            row['provider'] = 'sagafalabella'

                        if row['provider'] == 'plaza vea':
                            row['provider'] = 'plazavea'

                        all_data.append(row)
                        data_by_index.setdefault(index_date, []).append(row)

        # values = set()
        # values2 = set()
        # for item in all_data:
        #     values.add(item['provider'])
        #     values2.add(item['vendor'])
        # print(values)
        # print(values2)

        # saving in csv
        self.writing_file(all_data, "{}/all_data.csv".format(self.__data_path_out))

        # saving elk and mysql
        total = 0
        # connection = mysql.connector.connect(host=mysql_host,
        #                                      database=mysql_database,
        #                                      user=mysql_username,
        #                                      password=mysql_password)

        for index, products in data_by_index.items():
            print('---------------------------------------')
            print("Loading index {}".format(index))

            total += len(products)
            elastic_data = []
            mysql_data = []

            for product in products:
                elastic_data.append({
                    "_index": "{}-{}".format(self.__index, index),
                    "_type": "app",
                    "_source": json.dumps(product)
                })

                mysql_data.append((
                    product['product_id'], str(product['product_code']), product['provider'], str(product['vendor']),
                    product['url'], product['name'], str(product['brand']), product['amount_sold'], product['amount_available'],
                    product['currency'], product['pvp'], product['pvp_internet'], product['pvp_discount'], str(product['category']),
                    str(product['model']), str(product['img']), product['timestamp'], product['time_iso']
                ))

            # insert elastic
            try:
                helpers.bulk(self.__es, elastic_data)
                print("Documents inserted into elastic: {}".format(len(products)))
            except:
                print(traceback.format_exc())

            # insert mysql
            # try:
            #     sql_insert_query = """ INSERT INTO products (product_id,
            #                   product_code, provider, vendor, url, name, brand, amount_sold,
            #                   amount_available, currency, pvp, pvp_internet,
            #                   pvp_discount, category, model, img,timestamp, time_iso)
            #                                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) """
            #     cursor = connection.cursor(prepared=True)
            #     cursor.executemany(sql_insert_query, mysql_data)
            #     connection.commit()
            #
            #     print("Rows inserted into mysql: {}".format(cursor.rowcount))
            #
            #     cursor.close()
            # except:
            #     print(traceback.format_exc())

        # if connection.is_connected():
        #     connection.close()
        #     print("connection is closed")

        print("--> total: {}".format(total))
        print('--> end load')

    @staticmethod
    def writing_file(products, filename):
        file = open(filename, 'w')
        line = ['product_id', 'product_code', 'provider', 'vendor', 'url', 'name', 'brand', 'amount_sold', 'amount_available', 'currency', 'pvp',
                'pvp_internet', 'pvp_discount', 'category', 'model', 'img', 'timestamp', 'time_iso']
        file.write("|".join(line) + "\n")

        for product in products:
            try:
                data = [product['product_id'], str(product['product_code']), product['provider'], str(product['vendor']), product['url'],
                        product['name'], str(product['brand']), str(product['amount_sold']), str(product['amount_available']),
                        'S/.', str(product['pvp']), str(product['pvp_internet']), str(product['pvp_discount']),
                        product['category'], str(product['model']), str(product['img']), str(product['timestamp']), str(product['time_iso'])]
                line = "|".join(data)

                file.write(line + "\n")
            except:
                print(product)
                print(line)
                print(traceback.format_exc())
                break

        file.close()


LoadData('D:\\__Projects\\Dateme.pe\\data', 'D:\\__Projects\\Dateme.pe\\data_out')
