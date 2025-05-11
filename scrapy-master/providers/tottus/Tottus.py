# Created by Miguel Pazo (https://miguelpazo.com)
import hashlib
import sys
import time

from common.Utils import Utils
from database.model.model import ProviderItem
from driver.chrome import ChromeDriver
from logger.log import Log


class Tottus:
    __driver = None
    __provider_url = 'https://www.tottus.com.pe'
    __provider = 'Tottus'
    __datetime = None
    __save_path = '/opt/'

    def __init__(self):
        self.__driver = ChromeDriver()
        self.__datetime = Utils.get_current_date()

        if len(sys.argv) > 0:
            self.__save_path = sys.argv[1]

    def run(self):
        Log.info("Starting scrapping of {}".format(self.__provider_url))

        menu_links = self.get_menu_links()
        menu_links_filter = ['Cómputo', 'Audio', 'Cámaras', 'Videojuegos']

        for link in menu_links:
            if any(x in link[0] for x in menu_links_filter):
                categories = self.proc_menu(link)

                for category in categories:
                    self.proc_category(category)

        self.__driver.quit()

        Log.info("Finished scrapping of {}".format(self.__provider_url))

    def proc_category(self, category):
        links = []
        products = []
        productsFinal = []
        category_name = category[1]

        Log.info('===========================================')
        Log.info('===========================================')
        Log.info("-> Category: {}".format(category_name))
        Log.info("-> Url: {}".format(category[0]))
        Log.info("-> Total products: {}".format(category[2]))

        self.__driver.get(category[0])

        products = self.load_more()
        products_count = len(products)

        while True:
            products = self.load_more()

            if len(products) == products_count:
                break
            else:
                products_count = len(products)

        for product in products:
            elements = product.find_elements_by_tag_name('a')

            for element in elements:
                if element.get_attribute('href') != '':
                    links.append(element.get_attribute('href'))
                    break

        for index, link in enumerate(links):
            try:
                html = self.__driver.get(link)
                product = self.get_product(link, category_name, html, self.__provider, self.__datetime)
                Log.info("Progress: {}/{}".format(index + 1, len(links)))

                if product:
                    productsFinal.append(product)
            except Exception as e:
                Log.error("Wrong parsing: {}".format(link))
                pass

        Log.info("Total products loaded: {}".format(len(productsFinal)))

        # Writing file
        self.writing_file(self.__save_path, self.__provider, category_name, productsFinal)

    def proc_menu(self, menu):
        Log.info("-> Fetching category links for: {}".format(menu[1]))
        html = self.__driver.get(menu[0])
        categories = html.find(id='collapseFourMarca').find_all('li')
        links = []

        for category in categories:
            if category.input is not None:
                link = self.__provider_url + category.input.get('onclick').replace("window.location='", '')[0:-1]
                name = category.contents[2].strip()
                count = category.span.text.strip()
                links.append((link, name, count))

        Log.info("---> Total category links: {}".format(len(links)))

        return links

    def load_more(self):
        self.__driver.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(10)

        products = self.__driver.driver.find_elements_by_class_name('item-product-caption')

        return products

    def get_menu_links(self):
        Log.info('Fetching main menu links')

        html = self.__driver.get(self.__provider_url)
        menus = html.find(class_='sm-supermercado').find_next_siblings('li')
        links = []

        for menu in menus:
            menu_headers = menu.find_all('a', class_='menu-header-link')

            for menu_header in menu_headers:
                link = menu_header.get('href')
                name = menu_header.h4.text.strip()
                links.append((self.__provider_url + link, name))

        Log.info("Total main menu links: {}".format(len(links)))

        return links

    @staticmethod
    def get_product(url, category, html, provider, datetime):
        product = {}
        description = None

        # product name
        name = html.find('div', class_='caption-description').find('div', class_='title').h5.text.strip()
        name = ' '.join(name.split())

        # Getting prices
        price_local = html.find('div', class_='price-selector').find('span', class_='nule-price')
        price_online = html.find('div', class_='price-selector').find('span', class_='active-price').span.text.replace('S/', '').replace(',', '').strip()
        price_cc = html.find('div', class_='offer-details').find('span', class_='red')

        price_online = float(price_online)

        if price_local:
            price_local = price_local.text.replace('S/', '').replace(',', '').strip()
            price_local = float(price_local)
        else:
            price_local = price_online

        if price_cc:
            price_cc = price_cc.text.replace('S/', '').replace(',', '').strip()
            price_cc = price_cc[:price_cc.find('Exclusivo')].strip()
            price_cc = float(price_cc)
        else:
            price_cc = -1

        # Getting description
        section_description = html.find(class_='wrap-text-descriptions')
        phrases = section_description.find_all('p')

        if len(phrases) > 0:
            description = Utils.proc_name(phrases[1].text)

        # Getting model and specs
        table = section_description.find('table')
        specs = []
        model = None

        if table is not None:
            rows = table.find_all('tr')

            for row in rows:
                columns = row.find_all('td')
                field_name = Utils.proc_name(columns[0].text).replace(':', '')
                field_value = Utils.proc_name(columns[1].text).replace(':', '')

                if field_name == 'Modelo':
                    model = field_value

                specs.append("{}: {}".format(field_name, field_value))

        # product image
        img = html.find(id='elvzoom').get('src')

        # Getting categories
        breadcrumbs = []
        breadcrumb_section = html.find('div', class_='breadcrumb-nav').find('h3')
        breadcrumb_list = breadcrumb_section.find_all('a')
        breadcrumb_contents = breadcrumb_section.contents

        for breadcrumb in breadcrumb_list:
            breadcrumbs.append(Utils.proc_name(breadcrumb.text))

        breadcrumbs.append(Utils.proc_name(breadcrumb_contents[len(breadcrumb_contents) - 1].replace('/', '')))

        product['product_id'] = hashlib.sha256(url.encode()).hexdigest()
        product['product_code'] = None
        product['sku'] = None
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
        product['pvp_discount'] = price_cc
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


Tottus().run()
