# Created by Miguel Pazo (https://miguelpazo.com)
import hashlib
import sys
import time

from selenium.common.exceptions import NoSuchElementException

from common.Utils import Utils
from database.model.model import ProviderItem
from driver.chrome import ChromeDriver
from logger.log import Log


class Curacao:
    __driver = None
    __provider_url = 'https://www.lacuracao.pe'
    __provider = 'Curacao'
    __datetime = None
    __save_path = '/opt/'

    def __init__(self):
        self.__driver = ChromeDriver()
        self.__datetime = Utils.get_current_date()

        if len(sys.argv) > 0:
            self.__save_path = sys.argv[1]

    def run(self):
        Log.info("Starting scrapping of {}".format(self.__provider_url))
        # self.close_first_alert()

        menu_links = self.get_menu_links()
        menu_links_filter = ['computo']

        for link in menu_links:
            if any(x in link[0] for x in menu_links_filter):
                self.proc_category(link)

        self.__driver.quit()

        Log.info("Finished scrapping of {}".format(self.__provider_url))

    def close_first_alert(self):
        self.__driver.get(self.__provider_url)
        self.__driver.click("#onesignal-popover-cancel-button")
        time.sleep(10)

    def proc_category(self, category):
        links = []
        products = []
        productsFinal = []

        html = self.__driver.get(category[0])
        products_total = html.find('div', class_='header_bar').find(class_='title').text.strip()
        products_total = products_total.replace('Productos:', '').replace('(', '').replace(')', '').strip()
        category_name = category[1]

        Log.info('===========================================')
        Log.info('===========================================')
        Log.info("-> Category: {}".format(category_name))
        Log.info("-> Url: {}".format(category[0]))
        Log.info("-> Total products: {}".format(products_total))

        products = self.load_more()
        products_count = len(products)

        while True:
            products = self.load_more()

            if len(products) == products_count:
                break
            else:
                products_count = len(products)

        for product in products:
            try:
                element = product.find_element_by_class_name('product_name').find_element_by_tag_name('a')
                links.append(element.get_attribute('href'))
            except NoSuchElementException as ex:
                pass

        for index, link in enumerate(links):
            try:
                html = self.__driver.get(link)
                product = self.get_product(link, category_name, html, self.__provider, self.__datetime, self.__provider_url)
                Log.info("Progress: {}/{}".format(index + 1, len(links)))

                if product:
                    productsFinal.append(product)
            except Exception as e:
                Log.error("Wrong parsing: {}".format(link))
                pass

        Log.info("Total products loaded: {}".format(len(productsFinal)))

        # Writing file
        self.writing_file(self.__save_path, self.__provider, category_name, productsFinal)

    def load_more(self):
        self.__driver.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(10)

        products = self.__driver.driver.find_elements_by_class_name('product')

        return products

    def get_menu_links(self):
        Log.info('Fetching main menu links')

        html = self.__driver.get(self.__provider_url)
        menus = html.find(id='departmentsMenu').find_all('li')
        links = []

        for menu in menus:
            section_departments = menu.find('div', class_='departmentMenu')

            if section_departments is not None:
                departments = section_departments.find('ul', class_='categoryList').find_all('li')

                for department in departments:
                    if department.a.get('id').startswith('categoryLink'):
                        link = department.a.get('href')
                        name = department.a.text.strip()

                        if 'oferta' not in name.lower():
                            links.append((link, name))

        Log.info("Total main menu links: {}".format(len(links)))

        return links

    @staticmethod
    def get_product(url, category, html, provider, datetime, provider_url):
        product = {}
        description = None

        # product name
        name = html.find('h1', class_='main_header').text
        name = Utils.proc_name(name)

        # sku
        sku = html.find('span', class_='sku').text.strip()
        sku = sku.replace('SKU:', '')

        # Getting prices
        price_old = html.find('span', class_='old_price')
        price = html.find('span', class_='price')
        price_local = -1
        price_online = -1

        if price_old is not None:
            price_local = Utils.proc_price(price_old.text)
            price_online = Utils.proc_price(price.text)
        else:
            price_local = Utils.proc_price(price.text)

        # Getting description
        section_description = html.find(id='tab1Widget')

        if section_description is not None:
            description = section_description.find('p').text
            description = Utils.proc_name(description)

        # Getting model and specs
        section_specs = html.find(id='tab2Widget')
        specs = []
        model = None

        if section_specs is not None:
            rows = section_specs.find_all('li')

            for row in rows:
                columns = row.find_all('span')
                field_name = Utils.proc_name(columns[0].text).replace(':', '')
                field_value = Utils.proc_name(columns[1].text)

                if field_name == 'Modelo':
                    model = field_value

                specs.append("{}: {}".format(field_name, field_value))

        # product image
        img = provider_url + html.find(id='productMainImage').get('src')

        # Getting categories
        breadcrumbs = []
        breadcrumb_list = html.find(id='widget_breadcrumb').find_all('li')

        for breadcrumb in breadcrumb_list:
            if breadcrumb.a is not None:
                breadcrumbs.append(Utils.proc_name(breadcrumb.a.text))

        breadcrumbs = breadcrumbs[1:]

        product['product_id'] = hashlib.sha256(url.encode()).hexdigest()
        product['product_code'] = None
        product['sku'] = sku
        product['provider'] = provider
        product['brand'] = None
        product['model'] = model
        product['category'] = " -- ".join(breadcrumbs) if len(breadcrumbs) > 0 else category
        product['url'] = url
        product['name'] = name
        product['description'] = description
        product['technical_specs'] = " -- ".join(specs) if len(specs) > 0 else None
        product['pvp'] = price_local
        product['pvp_internet'] = price_online
        product['pvp_discount'] = -1
        product['amount_sold'] = -1
        product['amount_available'] = -1
        product['img'] = img
        product['timestamp'] = datetime[0]
        product['time_iso'] = datetime[1]

        return product

    @staticmethod
    def writing_file(path, provider, category, products):
        from datetime import datetime
        current_date = datetime.now().strftime('%Y%m%d_%H%M%S')
        category = category.replace(' ', '')

        filename = "{}{}-{}-{}".format(path, provider, category, current_date)
        ProviderItem().to_csv2(products, filename)


Curacao().run()
