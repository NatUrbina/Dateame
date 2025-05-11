from elasticsearch import Elasticsearch
from elasticsearch import helpers

username = 'b4aPKf8kQv'
password = 'Ci5LPNU4sJRXFBxnHj'
url = 'https://dateame-4602262096.us-east-1.bonsaisearch.net'
index_src = 'products'
index_dest = 'products_searchable'


class Cleaner:
    __es = None
    dict_of_duplicate_docs = {}

    def __init__(self):
        self.__es = Elasticsearch([url], http_auth=(username, password))
        print(self.__es.info())

        # Recreating the index..
        # ignore 400 cause by IndexAlreadyExistsException when creating an index
        self.__es.indices.delete(index=index_dest, ignore=[400, 404])
        self.__es.indices.create(index=index_dest, ignore=400)

    def run(self):
        self.scroll_over_all_docs()
        self.insert_not_repeated()

    def scroll_over_all_docs(self):
        data = self.__es.search(index=index_src, scroll='1m', size=1000, body={"query": {"match_all": {}}})
        sid = data['_scroll_id']
        scroll_size = len(data['hits']['hits'])
        self.populate_dict_of_duplicate_docs(data['hits']['hits'])

        while scroll_size > 0:
            data = self.__es.scroll(scroll_id=sid, scroll='2m')
            print("Getting scroll: {}".format(scroll_size))
            self.populate_dict_of_duplicate_docs(data['hits']['hits'])
            sid = data['_scroll_id']
            scroll_size = len(data['hits']['hits'])

    def populate_dict_of_duplicate_docs(self, hits):
        for item in hits:
            _id = item["_id"]
            product_code = item['_source']["product_code"]
            price = item['_source']["price"]
            self.dict_of_duplicate_docs.setdefault(product_code, []).append((_id, price))

    def insert_not_repeated(self):
        ids = []
        data = []
        size = 100

        for product_code, products in self.dict_of_duplicate_docs.items():
            idInsert = products[0][0]
            price = products[0][1]

            for product in products:
                if (product[1] < price):
                    price = product[1]
                    idInsert = product[0]

            if idInsert != '':
                ids.append(idInsert)

        for list in self.chunker(ids, size):
            result = self.__es.search(index=index_src, size=size, body={"query": {"ids": {"values": list}}})

            for doc in result['hits']['hits']:
                data.append({
                    "_index": index_dest,
                    "_type": "app",
                    "_source": doc['_source']
                })

        print(helpers.bulk(self.__es, data))

    @staticmethod
    def chunker(seq, size):
        return (seq[pos:pos + size] for pos in range(0, len(seq), size))


Cleaner().run()
