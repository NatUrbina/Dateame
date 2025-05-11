# Created by Miguel Pazo (https://miguelpazo.com)
import hashlib
import sys
import time

from common.Utils import Utils
from database.model.model import ProviderItem
from driver.chrome import ChromeDriver
from logger.log import Log


class Lumingo:
    __driver = None
    __provider_url = 'https://www.lumingo.com'
    __provider = 'Lumingo'
    __datetime = None
    __save_path = '/opt/'

    def __init__(self):
        self.__driver = ChromeDriver()
        self.__datetime = Utils.get_current_date()

        if len(sys.argv) > 0:
            self.__save_path = sys.argv[1]

    def run(self):
        Log.info("Starting scrapping of {}".format(self.__provider_url))

        link = 'https://www.lumingo.com/producto/notebook-lenovo-v130-14ikb2c-14c2b4c2b428-81hq00l5lm-29-core-i3-1tb-4gb/p/000000000004606614'
        html = self.__driver.get(link)
        product = self.get_product(link, 'otro', html, self.__provider, self.__datetime)
        print(product)

        # menu_links = self.get_menu_links()
        # menu_links_filter = ['celulares', 'gamer', 'computo']
        #
        # for link in menu_links:
        #     if any(x in link[0] for x in menu_links_filter):
        #         categories = self.proc_menu(link)
        #
        #         for category in categories:
        #             self.proc_category(category)
        #             break

        self.__driver.quit()

        Log.info("Finished scrapping of {}".format(self.__provider_url))

    def proc_category(self, category):
        links = []
        products = []
        productsFinal = []

        html = self.__driver.get(category[0])
        products_total = html.find('div', class_='total--results--items').text.strip()
        products_total = products_total.replace('Items)', '').replace('(', '').strip()
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
            element = product.find_element_by_class_name('product--image-container').find_element_by_tag_name('a')
            links.append(element.get_attribute('href'))

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
        categories = html.find(id='product-facet').div.find(class_='js-facet').find('ul', class_='facet__list').find_all('li')
        links = []

        for category in categories:
            category_link = self.__provider_url + category.span.a.get('href')
            category_name = category.span.a.text.strip()
            links.append((category_link, category_name))

        Log.info("---> Total category links: {}".format(len(links)))

        return links

    def load_more(self):
        self.__driver.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(10)

        products = self.__driver.driver.find_elements_by_class_name('product-item')

        return products

    def get_menu_links(self):
        Log.info('Fetching main menu links')

        html = self.__driver.get(self.__provider_url)
        menus = html.find_all('ul', class_='nav__links--products')
        menu_desktop = None
        links = []

        for menu in menus:
            if 'mobile' not in menu.get('class'):
                menu_desktop = menu

        if menu_desktop is not None:
            menu_primary = menu_desktop.find_all('li', class_='nav__links--primary')

            for element in menu_primary:
                if element.span.a is not None:
                    name = element.span.a.get('title')
                    link = element.span.a.get('href')

                    links.append((self.__provider_url + link, name))

        Log.info("Total main menu links: {}".format(len(links)))

        return links

    @staticmethod
    def get_product(url, category, html, provider, datetime):
        product = {}
        description = None

        # product name
        name = html.find('h1', class_='name').text
        name = Utils.proc_name(name)

        # Getting sku
        sku = None
        page_title = html.find('div', class_='page-title')

        if len(page_title.contents) > 0:
            sku = page_title.contents[1].replace('Código', '').replace(':', '').strip()

        # Getting prices
        main_price = html.find('div', class_='main-price')
        price = main_price.find('p', class_='price').span.text.strip()
        price_old = main_price.find('div', class_='price--line--through').span.text.strip()
        price_local = -1
        price_online = -1

        if price_old == '':
            price_local = Utils.proc_price(price)
        else:
            price_local = Utils.proc_price(price_old)
            price_online = Utils.proc_price(price)

        # Getting description
        dropdown_headers = html.find(class_='product--dropdown').find_all(class_='dropdown--header')
        section_description = None
        section_specs = None

        for header in dropdown_headers:
            if header.get('id') is None:
                section_description = header.find_next_sibling(class_='dropdown--body')
            elif header.get('id') == 'tabespecificaciones':
                section_specs = header.find_next_sibling(class_='dropdown--body')

        if section_description is not None:
            description = section_description.find(class_='tab-details').p.text
            description = Utils.proc_name(description)

        # Getting model, brand and specs
        specs = []
        model = None
        brand = None

        if section_specs is not None:
            classifications = section_specs.find_all('div', class_='circle--classifications')

            for classification in classifications:
                description_spec = classification.find_next_sibling().text.strip().split(':')

                if len(description_spec) > 1:
                    field_name = Utils.proc_name(description_spec[0]).replace('.', '')
                    field_value = Utils.proc_name(description_spec[1]).replace('.', '')

                    if field_name == 'Modelo':
                        model = field_value

                    if 'Marca' in field_name:
                        brand = field_value
                else:
                    field_name = 'Otro'
                    field_value = description_spec[0].replace('.', '')

                specs.append("{}: {}".format(field_name, field_value))

        # product image
        img = None
        images = html.find_all(class_='atm-imagen-producto')

        for image in images:
            if image.get('src') is not None:
                img = image.get('src')

        # Getting categories
        breadcrumbs = []
        breadcrumb_list = html.find(class_='breadcrumb-section').find_all('li')

        for breadcrumb in breadcrumb_list:
            if breadcrumb.a is not None:
                breadcrumbs.append(Utils.proc_name(breadcrumb.a.text))

        product['product_id'] = hashlib.sha256(url.encode()).hexdigest()
        product['product_code'] = None
        product['sku'] = sku
        product['provider'] = provider
        product['brand'] = brand
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


Lumingo().run()
