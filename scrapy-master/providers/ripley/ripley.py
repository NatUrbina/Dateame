from datetime import datetime
import time

from selenium.webdriver.common.by import By

from database.model.model import ProviderItem
from logger.log import Log
from providers.provider import Provider

root = "https://simple.ripley.com.pe"
provider_name = "Ripley"


class RipleyProvider(Provider):
    __provider_url = None

    def __init__(self, url):
        self.__provider_url = url
        super().__init__()

    def run(self):

        Log.info("Starting scrapping of {}".format(self.__provider_url))

        items = []
        html = self.driver.get(self.__provider_url, [".pagination"])

        category = self.get_category(html)

        previous_url = self.__provider_url

        while True:
            print(len(items))
            items += self.get_urls(html)
            if self.has_more_pages(html):

                try:
                    self.driver.driver.find_element(By.LINK_TEXT, "»").click()
                except:
                    pass
                time.sleep(1)

                retries = 0
                while previous_url == self.driver.get_url():
                    try:
                        self.driver.driver.find_element(By.LINK_TEXT, "»").click()
                    except:
                        pass

                    retries += 1
                    if retries == 3:
                        self.driver.get(previous_url, [".pagination"])
                        break
                    time.sleep(5)

                previous_url = self.driver.get_url()
                print(previous_url)
                html = self.driver.get_source([".pagination"])
            else:
                print("No more pages found")
                break

        items = set(items)
        Log.info("Found {} total items".format(len(items)))

        data = []
        for item_url in set(items):
            item = {"url": "{}{}".format(root, item_url),
                    "provider": provider_name}

            print(item)
            try:
                html = self.driver.get(item["url"], [".product-info"])
            except:
                Log.error(item["url"])
                continue

            aux = self.get_item((html, category))
            data.append({**item, **aux})

        self.driver.quit()

        # writing to file
        current_date = datetime.now().strftime('%Y%m%d')
        filename = "/home/ktodorov/projects/scrapy/data/{}-{}".format(provider_name, current_date)
        ProviderItem().to_csv(data, filename)

        Log.info("Finished scrapping of {}".format(provider_name))

    def has_more_pages(self, html):
        pagination = html.find(class_="pagination")
        uls = pagination.find_all("li")
        if uls[-1].find(class_="is-disabled") is None:
            return True
        else:
            return False

    def get_urls(self, html):

        urls = []
        catalog = html.find(class_="catalog-container")
        items = catalog.find_all(class_="catalog-product-item")

        for i in items:
            item_url = i.get("href")
            urls.append("{}".format(item_url))

        return urls

    @staticmethod
    def get_category(html):

        category = []
        breadcrumbs = html.find(class_="breadcrumbs").find_all(class_="breadcrumb")
        for b in breadcrumbs:
            category.append(b.text)

        return " -- ".join(category)

    @staticmethod
    def get_item(html):
        """
        Given item html, gets all the information about
        :param html:
        :return: dict with item info
        """
        category = html[1]
        html = html[0]

        pvp = None
        try:
            pvp = html.find(class_="product-normal-price").find(class_="product-price").text
        except:
            pass

        pvp_internet = ""
        try:
            pvp_internet = html.find(class_="product-internet-price-not-best")
            if pvp_internet is None:
                pvp_internet = html.find(class_="product-internet-price")

            pvp_internet = pvp_internet.find(class_="product-price").text
            if pvp is None:
                pvp = pvp_internet
        except Exception as e:
            Log.error(e)

        pvp_discount = ""
        try:
            pvp_discount = html.find(class_="product-ripley-price").find(class_="product-price").text
        except:
            pass

        item = {ProviderItem.category: category,
                ProviderItem.amount_available: "",
                ProviderItem.amount_sold: "",
                ProviderItem.brand: html.find(class_="brand-logo").text,
                ProviderItem.name: html.find(class_="product-header").h1.text,
                ProviderItem.pvp: pvp,
                ProviderItem.pvp_discount: pvp_discount,
                ProviderItem.pvp_internet: pvp_internet,
                ProviderItem.img: html.find(class_="owl-wrapper")
                    .find_all(class_="owl-item")[0].div.img.get("src")
                }

        item = RipleyProvider.get_brand_model(item)

        return item

    @staticmethod
    def get_brand_model(item):

        c = item["category"]

        categoria = "Otros"

        if "Smartphones" in c:
            categoria = "smartphones"
        elif "Cómputo" in c:
            categoria = "computacion"
        elif "Fotografia" in c:
            categoria = "camaras"

        item[ProviderItem.category] = categoria

        return item


category_urls = ["https://simple.ripley.com.pe/entretenimiento/fotografia/todo-fotografia",
                 "https://simple.ripley.com.pe/celulares/smartphones/todo-celulares",
                 "https://simple.ripley.com.pe/computo/laptops/todas-las-laptops"]

start = datetime.now()
for u in category_urls:
    RipleyProvider(u).run()
print(start)
print(datetime.now())
