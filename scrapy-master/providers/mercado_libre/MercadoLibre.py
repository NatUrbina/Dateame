import os
import traceback

from datetime import datetime


import selenium
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from database.model.model import ProviderItem
from driver.chrome import ChromeDriver
from logger.log import Log
from providers.provider import Provider

import json

provider_name = "MercadoLibre"


class MercadoLibreProvider(Provider):
    __provider_url = None

    def __init__(self, url):
        super().__init__()
        self.__provider_url = url

    def run(self, provider_name):
        # Getting all the pages for provider

        Log.info("Starting scrapping of {}".format(self.__provider_url))

        provider_pages = [self.__provider_url]
        has_more = True
        while has_more:
            last = provider_pages[len(provider_pages) - 1]
            (pages, has_more) = self.get_pages(last)
            provider_pages += pages

        pages = list(set(provider_pages))

        Log.info("Found {} pages".format(len(pages)))

        urls = []
        for page in pages:
            page_urls = self.get_urls(page)
            urls += page_urls

        del pages

        urls = set(urls)
        Log.info("Found {} total items".format(len(urls)))

        # Extracting all items data from pages previously found
        data = []

        current_count = 0
        max_count = len(urls)
        for url in set(urls):
            current_count += 1
            print("{}/{}   =>   {}".format(current_count, max_count, url))
            html = self.driver.get(url, ["#short-desc"])
            try:
                item = self.get_item(html.body)
            except Exception as e:
                Log.error("Wrong parsing: {}".format(url))
                continue
            html.html.decompose()
            del html
            item[ProviderItem.url] = url
            item[ProviderItem.provider] = provider_name

            data.append(item)

        self.driver.quit()

        # writing to file
        current_date = datetime.now().strftime('%Y%m%d')
        filename = "/home/ktodorov/projects/scrapy/data/{}-{}".format(provider_name, current_date)

        Log.info("Writting all {} items into file {}".format(len(data), filename))

        ProviderItem().to_csv(data, filename)

        Log.info("Finished scrapping of {}".format(self.__provider_url))

    def get_urls(self, page):
        urls = []
        html = self.driver.get(page)

        tablaResultados = html.find(id="searchResults")
        for item in tablaResultados.find_all(class_="rowItem"):
            urls.append(item.find(class_="item__image").find(class_="images-viewer").get("item-url"))

        return urls

    def get_pages(self, url):
        pages = [url]
        html = self.driver.get(url, [".pagination__container"])

        pagination_container = html.find(class_="pagination__container")
        for pagination in pagination_container.find_all(class_="andes-pagination__button"):
            # Previuos or current
            if (pagination.a.string) is None or (pagination.a.string == "#"):
                continue
            if pagination.a.get("href") == "#":
                continue

            pages.append(pagination.a.get("href"))

        out = (pages, self.has_more_pages(html))
        html.decompose()
        return out

    def has_more_pages(self, html):

        next = html.find(class_="andes-pagination__button--next")
        if next is None or "andes-pagination__button--disabled" in next['class']:
            return False
        else:
            return True

    def get_item(self, html):
        item = {}

        # desc
        short_desc = html.find(id="short-desc")

        # Item name
        name = short_desc.find(class_="item-title__primary").string.replace("\n", "").replace("\t", "")
        item[ProviderItem.name] = name

        try:
            amount_sold = short_desc.find(class_="item-conditions").string.replace("\n", "").replace("\t", "") \
                .replace("Nuevo", "").replace("Usado", "").replace("vendidos", "").replace("\xa0", "").replace("-", "") \
                .replace("vendido", "")
        except:
            Log.error("Error finding amount sold ")
            amount_sold = 0

        try:
            amount_available = short_desc.find(class_="dropdown-quantity-available").string \
                .replace("\n", "").replace("\t", "").replace(" ", "").replace("(", "").replace(")", "").replace(
                "disponibles", "")
        except Exception as e:
            Log.warn("Error finding available amount ")
            amount_available = 1

        currency = short_desc.find(class_="price-tag-symbol").string
        pvp = float(short_desc.find(class_="price-tag-fraction").string.replace(".", ""))

        breadcrumbs = html.find_all(class_="breadcrumb")
        category = []
        for c in breadcrumbs:
            category.append(c.string.replace("\n", "").replace("\t", ""))

        # Images
        item[ProviderItem.img] = ""

        images = html.find(class_="gallery-content item-gallery__wrapper").get("data-full-images")
        image_list = json.loads(images)
        for image in image_list:
            item[ProviderItem.img] = image.get("src", "")
            break

        if amount_sold == '':
            item[ProviderItem.amount_sold] = 0
        else:
            item[ProviderItem.amount_sold] = int(amount_sold)

        if amount_sold == '':
            item[ProviderItem.amount_available] = 0
        else:
            try:
                item[ProviderItem.amount_available] = int(amount_available)
            except:
                item[ProviderItem.amount_available] = 0

        item[ProviderItem.currency] = currency
        item[ProviderItem.pvp] = pvp
        item[ProviderItem.pvp_discount] = pvp
        item[ProviderItem.pvp_internet] = pvp
        item[ProviderItem.category] = " -- ".join(category)

        item = self.get_brand_model(item)

        return item

    @staticmethod
    def get_brand_model(item):

        c = item["category"]

        categoria = "Otros"
        marca = "Otros"
        modelo = "Otros"

        splitted = c.split(" -- ")
        if "Celulares y Smartphones" in c:
            index = splitted.index("Celulares y Smartphones")
            info = splitted[index:]

            categoria = "smartphones"
            marca = info[1]
            modelo = " ".join(info[2:])

            if marca == "iPhone":
                marca = "Apple"

        elif "Computación" in c:
            splitted = splitted[1:]

            if splitted[0] == "Apple":
                marca = "Apple"

                if splitted[1] in ("Macbook", "Computadoras"):
                    categoria = "computacion"
                    modelo = splitted[2]
                elif splitted[1] in ("Accesorios"):
                    categoria = "accesorios_computacion"

            elif splitted[0] == "Laptops":
                categoria = "computacion"
                marca = splitted[1]

            elif splitted[0] == "iPad y Tablets":
                categoria = "tablets"
                if splitted[1] == "iPad":
                    marca = "Apple"
                    modelo = " ".join(splitted[2:])
                else:
                    marca = splitted[1]
            else:
                pass
                # print(splitted)

        elif "Cámaras y Accesorios" in c:
            splitted = splitted[1:]

            if splitted[0] == "Cámaras Reflex/Pro":
                categoria = "camaras"
                marca = splitted[1]
            elif splitted[0] == "Video Cámaras":
                categoria = "camaras"
                marca = splitted[2]
            elif splitted[0] == "Cámaras Convencionales":
                categoria = "camaras"
            elif splitted[0] == "Accesorios para Cámaras":
                categoria = "accesorios_camaras"
            else:
                pass
        #             print(splitted)

        elif "Consolas y Videojuegos" in c:
            categoria = "consolas_videojuegos"

        item[ProviderItem.category] = categoria
        item[ProviderItem.brand] = marca
        item[ProviderItem.model] = modelo

        return item

start = datetime.now()

urls = [
    ("https://listado.mercadolibre.com.pe/_CustId_84683920", provider_name + "-1"),  # wienerstech
    ("https://listado.mercadolibre.com.pe/_CustId_146232397", provider_name + "-2"),  # miraflores
    ("https://listado.mercadolibre.com.pe/_CustId_3601594", provider_name + "-3"),  # beauritz
    ("https://listado.mercadolibre.com.pe/_CustId_249990499", provider_name + "-4"),  # ELECTRO-CYBER
    ("https://listado.mercadolibre.com.pe/_CustId_187749618", provider_name + "-5"),  # DUVAL IMPORT
    ("https://listado.mercadolibre.com.pe/_CustId_190082939", provider_name + "-6"),  # FORTUM4+STORE
    ("https://listado.mercadolibre.com.pe/_CustId_157013795", provider_name + "-7"),  # AMPTECHNOLOGY
    ("https://listado.mercadolibre.com.pe/camaras/_CustId_151026530_seller*id_151026530", provider_name + "-8"), # techimports01
    ("https://computacion.mercadolibre.com.pe/_CustId_151026530_seller*id_151026530", provider_name + "-8"), # techimports01
    ("https://listado.mercadolibre.com.pe/telefonia/_CustId_151026530_seller*id_151026530", provider_name + "-8"), # techimports01
    ("https://listado.mercadolibre.com.pe/_CustId_94968151", provider_name + "-9") # UNALUKA
]


import logging
import threading

def thread_function(url):
    MercadoLibreProvider(url[0]).run(url[1])

workers = []

for u in urls:
    workers.append(threading.Thread(target=thread_function, args=(u,)))

for w in workers:
    w.start()

for w in workers:
    w.join()

print(start)
print(datetime.now())
