import traceback

from driver.chrome import ChromeDriver
from logger.log import Log

root = "https://www.falabella.com.pe"


class SagaFalabellaProvider:
    __driver = None
    __provider_url = None

    def __init__(self, url):

        self.__driver = ChromeDriver()
        self.__provider_url = url

    def run(self, provider_name):
        # Getting all the pages for provider

        Log.info("Starting scrapping of {}".format(self.__provider_url))

        # Gets a all the items
        items = []
        print(self.__provider_url)
        html = self.__driver.get(self.__provider_url, [".box-list-numbers-bottom"])
        while True:
            items += self.get_urls(html)
            print(len(items))
            if self.has_more_pages(html):
                self.__driver.click_parent(".content-text-number-list .icon-right")
                html = self.__driver.get_source([".box-list-numbers-bottom"])
            else:
                print("No more pages found")
                break

        # writing to file
        from datetime import datetime
        current_date = datetime.now().strftime('%Y%m%d')

        filename = "/home/ktodorov/projects/scrapy/data/{}.txt".format(provider_name + "-" + current_date)
        file = open(filename, 'w')
        line = ["url", "provider", "name", "brand", "amount_sold",
                "amount_available", "currency", "pvp",
                "category", "img"]
        print("|".join(line))
        file.write("|".join(line) + "\n")

        # Get item info
        for item_url in set(items):
            item = {"url": "{}{}".format(root, item_url),
                    "provider": provider_name}

            try:
                html = self.__driver.get(item["url"], ["#js-fb-pp-photo__zoom"])
            except:
                print(item["url"])
                print(traceback.print_exc())
                continue

            aux = self.get_item(html)
            item = {**item, **aux}

            try:
                line = [item["url"], provider_name, item["name"], item["brand"], str(item["amount_sold"]),
                        str(item["amount_available"]), str(item["currency"]), str(item["pvp"]),
                        item["category"], item["img"]]
                print("|".join(line))
                file.write("|".join(line) + "\n")
            except Exception as e:
                print(item)
                print(traceback.format_exc())
                continue

        Log.info("Finished scrapping of {}".format(provider_name))
        self.__driver.quit()

    @staticmethod
    def get_urls(html):

        items = []
        pod_items = html.find_all(class_="pod-item")
        for item in pod_items:
            pod_body = item.find(class_="pod-body")
            anchor = pod_body.a
            href = anchor.get("href")
            print(href)
            items.append(href)

        return items

    def has_more_pages(self, html):
        icons = html.find_all(class_="icon-right")
        for icon in icons:
            if "hidden-button" in icon.parent["class"]:
                return False

        return True

    @staticmethod
    def get_item(html):
        """
        Given item html, gets all the information about
        :param html:
        :return: dict with item info
        """
        item = {}
        breadcrumbs = html.find(class_="fb-masthead__breadcrumb__links") \
            .find_all(class_="fb-masthead__breadcrumb__link")
        category = []
        for c in breadcrumbs:
            category.append(c.span.text.replace("\xa0", "").replace("\n", "").replace("\t", ""))
        item["category"] = " -- ".join(category).replace("/", "")

        brand = html.find(class_="fb-product-cta__brand").text
        item["brand"] = brand

        prices = html.find_all(class_="fb-price")[0].text  # usually first is the smallest
        item["pvp"] = prices.split("  ")[1]
        item["currency"] = prices.split("  ")[0]

        name = html.find(class_="fb-product-cta__title").text
        item["name"] = name

        img = html.find(id="js-fb-pp-photo__media").get("src")
        item["img"] = img[2:]

        item["amount_available"] = ""
        item["amount_sold"] = ""

        return item


SagaFalabellaProvider("{}/falabella-pe/category/cat50678/Computadoras".format(root)) \
    .run("Sagafalabella-Computadoras")
