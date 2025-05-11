# Created by Miguel Pazo (https://miguelpazo.com)
import hashlib
import json
import sys
import time

from selenium.common.exceptions import NoSuchElementException

from common import Utils
from common.Utils import Utils
from database.model.model import ProviderItem
from driver.chrome import ChromeDriver
from logger.log import Log


class PlazaVea:
    __driver = None
    __provider_url = 'https://www.plazavea.com.pe/supermercado'
    __provider = 'PlazaVea'
    __datetime = None
    __save_path = '/opt/'

    def __init__(self):
        self.__driver = ChromeDriver()
        self.__datetime = Utils.get_current_date()

        if len(sys.argv) > 0:
            self.__save_path = sys.argv[1]

    def run(self):
        Log.info("Starting scrapping of {}".format(self.__provider_url))

        category_links = self.get_menu_links()
        menu_links_filter = ['audio', 'videojuegos', 'computo', 'fotografia']

        for link in category_links:
            if any(x in link[0] for x in menu_links_filter):
                categories = self.proc_menu(link)

                for category in categories:
                    self.proc_category(category)
                    break

        self.__driver.quit()

        Log.info("Finished scrapping of {}".format(self.__provider_url))

        Log.info("======================================")
        Log.info("==== Resume:")
        Log.info("==== Started at: {}".format(self.__datetime[1]))
        Log.info("==== Ended at: {}".format(Utils.get_current_date()[1]))
        Log.info("======================================")

    def proc_category(self, category):
        links = []
        products = []
        productsFinal = []

        html = self.__driver.get(category[0])
        products_total = html.find(class_='Similar__content__count__total').text.strip()
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

        for item in products:
            try:
                category = item.find_element_by_class_name('Showcase__link')
                links.append(category.get_attribute('href'))
            except NoSuchElementException as ex:
                pass

        for index, category in enumerate(links):
            try:
                html = self.__driver.get(category)
                product = self.get_product(html, self.__provider, self.__datetime)
                Log.info("Progress: {}/{}".format(index + 1, len(links)))

                if product:
                    productsFinal.append(product)
            except Exception as e:
                Log.error("Wrong parsing: {}".format(category))
                pass

        Log.info("Total products loaded: {}".format(len(productsFinal)))

        # Writing file
        self.writing_file(self.__save_path, self.__provider, category_name, productsFinal)

    def proc_menu(self, menu_link):
        Log.info("-> Fetching category links for: {}".format(menu_link[1]))

        html = self.__driver.get(menu_link[0])
        menus = html.find('div', class_='menu-departamento').find('div', class_='search-single-navigator').find_all('li')
        links = []

        for menu in menus:
            link = menu.a.get('href')
            name = menu.text.strip()
            name = name[:name.index('(')].strip()

            links.append((link, name))

        Log.info("---> Total category links: {}".format(len(links)))

        return links

    def load_more(self):
        self.__driver.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        self.__driver.driver.execute_script(
            "return document.getElementById('normal-popover') ? document.getElementById('normal-popover').remove() : true")
        self.__driver.driver.execute_script(
            "elements=document.getElementsByClassName('header');elements[0]?elements[0].parentNode.removeChild(elements[0]):true;")

        products_prev = self.__driver.driver.find_elements_by_class_name('g-producto')
        products = products_prev

        retries = 0
        clicked = False
        while not clicked:
            try:
                # loadMore = self.__driver.driver.find_element_by_id('clickLoading')

                self.__driver.click("#clickLoading")
                # loadMore.click()

                t = 1
                while len(products_prev) == len(products) and t < 60:
                    time.sleep(1)
                    products = self.__driver.driver.find_elements_by_class_name('g-producto')
                    t += 1

                clicked = True
            except NoSuchElementException as ex:
                clicked = True
            except Exception as e:
                self.__driver.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                retries += 1
                Log.info(e)
                if retries == 20:
                    break
                time.sleep(1 * retries)

        products = self.__driver.driver.find_elements_by_class_name('g-producto')

        return products

    def get_menu_links(self):
        Log.info('Fetching main menu links')

        html = self.__driver.get(self.__provider_url)
        menus = html.find(class_='h-megamenu').find_all('a', class_='hmi-link n1')
        links = []

        for menu in menus:
            link = menu.get('href')
            name = menu.em.text.strip()

            links.append((link, name))

        Log.info("Total main menu links: {}".format(len(links)))

        return links

    @staticmethod
    def get_product(html, provider, datetime):
        product = {}
        pivot_start = 'vtex.events.addData('
        pivot_end = ');'

        html_string = str(html)
        start = html_string.find(pivot_start)
        end = html_string.find(pivot_end, start)
        json_string = html_string[start + len(pivot_start):end]

        try:
            json_parsed = json.loads(json_string)
        except:
            Log.info("Product not exist: {}".format(json_string))
            return None

        # Validating 404
        if json_parsed['pageCategory'] == '404':
            return None

        # Validating url
        url = json_parsed['pageUrl']

        if not url:
            return None

        # Validating stock
        stock = 0

        for key in json_parsed['skuStocks']:
            stock = json_parsed['skuStocks'][key]
            break

        if stock == 0:
            return None

        # Getting model and specs
        table_specs = html.find('table', class_='Especificaciones')
        specs = []
        model = None

        if table_specs is not None:
            model_row = table_specs.find_all(class_='Modelo')

            if len(model_row) > 0:
                model = model_row[1].text.strip()

            table = table_specs.find_all('tr')

            for row in table:
                field_name = Utils.proc_name(row.find(class_='name-field').text).replace(':', '')
                field_value = Utils.proc_name(row.find(class_='value-field').text)
                specs.append("{}: {}".format(field_name, field_value))

        # Getting description
        section_description = html.find(class_='productDescription')
        description = None

        if section_description.text != '':
            description = Utils.proc_name(section_description.text)

        discountCC = html.find('p', class_='toh')

        product['product_id'] = hashlib.sha256(url.encode()).hexdigest()
        product['product_code'] = None
        product['sku'] = None
        product['url'] = url
        product['provider'] = provider
        product['brand'] = Utils.proc_name(json_parsed['productBrandName'])
        product['model'] = model
        product['category'] = " -- ".join([Utils.proc_name(json_parsed['pageDepartment']), Utils.proc_name(json_parsed['productDepartmentName']), Utils.proc_name(json_parsed['productCategoryName'])])
        product['name'] = Utils.proc_name(json_parsed['productName'])
        product['description'] = description
        product['technical_specs'] = " -- ".join(specs) if len(specs) > 0 else None
        product['pvp'] = Utils.proc_price(json_parsed['productListPriceTo'])
        product['pvp_internet'] = Utils.proc_price(json_parsed['productPriceTo'])
        product['pvp_discount'] = Utils.proc_price(discountCC.contents[0].text) if discountCC is not None else -1
        product['amount_sold'] = -1
        product['amount_available'] = stock
        product['img'] = html.find(id='image-main').get('src').strip()
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


PlazaVea().run()
