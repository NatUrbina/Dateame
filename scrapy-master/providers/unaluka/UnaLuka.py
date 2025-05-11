# Created by Miguel Pazo (https://miguelpazo.com)
import hashlib
import sys
import urllib.parse

from common.Utils import Utils
from database.model.model import ProviderItem
from driver.chrome import ChromeDriver
from logger.log import Log


class UnaLuka:
    __driver = None
    __providerUrl = 'https://www.unaluka.com/'
    __provider = 'UnaLuka'
    __datetime = None
    __save_path = '/opt/'

    def __init__(self):
        self.__driver = ChromeDriver()
        self.__datetime = Utils.get_current_date()

        if len(sys.argv) > 0:
            self.__save_path = sys.argv[1]

    def run(self):
        Log.info("Starting scrapping of {}".format(self.__providerUrl))

        categories = self.get_menu_links()

        for category in categories:
            self.proc_category(category)

        self.__driver.quit()

        Log.info("Finished scrapping of {}".format(self.__providerUrl))

        Log.info("======================================")
        Log.info("==== Resume:")
        Log.info("==== Started at: {}".format(self.__datetime[1]))
        Log.info("==== Ended at: {}".format(Utils.get_current_date()[1]))
        Log.info("======================================")

    def proc_category(self, category):
        links = []
        productsFinal = []
        link = category[1]
        category_name = category[1]

        Log.info('===========================================')
        Log.info('===========================================')
        Log.info("-> Category: {}".format(category_name))
        Log.info("-> Url: {}".format(category[0]))

        while link != '':
            html = self.__driver.get(link)
            links += self.get_products_links(html)

            pages = html.find('ul', class_='pagination')

            if pages:
                pages = pages.find_all('li')
                link = pages[len(pages) - 2].a.get('href')
                last_class = pages[len(pages) - 1].get('class')
                last_class = last_class[0] if last_class and len(last_class) > 0 else ''

                link = link if last_class != 'active' else ''
            else:
                link = ''

        Log.info("Total products in category: {}".format(len(links)))

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

    def get_menu_links(self):
        html = self.__driver.get(self.__providerUrl)
        menu = html.find(class_='megamenu')
        categories = menu.find_all(class_='parent dropdown aligned-left')

        links = []
        linksExtra = [('Gaming', 'https://www.unaluka.com/Gaming'), ('Navajas', 'https://www.unaluka.com/Unaluka-Navajas')]

        for category in categories:
            if category.a.get('href') != '#':
                links.append((category.a.span.text.strip(), category.a.get('href')))

        links += linksExtra

        return links

    @staticmethod
    def get_products_links(html):
        products = html.find_all('div', class_='product-block')
        links = []

        for product in products:
            link = product.find(class_='img').get('href')

            if link != '' and link != '#':
                links.append(link)

        return links

    @staticmethod
    def get_product(link, category, html, provider, datetime):
        product = {}
        brand = None
        model = None
        pvp = -1
        pvp_internet = -1
        name = html.find('h1', class_='title-product')

        if not name:
            return None

        # Getting brand and model
        model_brand = html.find('ul', class_='list-unstyled description').find_all('li')

        if model_brand and len(model_brand) > 1:
            if model_brand[0].a:
                brand = model_brand[0].a.text.strip()
                brand = Utils.proc_name(brand)
            else:
                brand = None

        # Getting technical specs and model
        section_specs = html.find(id='tab-description')
        specs = []

        if section_specs.text != '':
            table = section_specs.find('table').find_all('tr')

            for row in table:
                columns = row.find_all('td')

                if len(columns) > 0:
                    field_name = columns[0].find('span')
                    field_value = columns[1].find('span')

                    field_name = field_name.text if field_name is not None else columns[0].text
                    field_value = field_value.text if field_value is not None else columns[1].text

                    field_name = Utils.proc_name(field_name).replace(':', '')
                    field_value = Utils.proc_name(field_value).replace(':', '')

                    if field_name == 'Modelo':
                        model = field_value

                    specs.append("{}: {}".format(field_name, field_value))

        # Getting prices
        price_span = html.find('span', class_='text-price')
        price_content = price_span.text.strip().replace('S/', '').replace(',', '').strip()
        pvp_internet = float(price_content)

        old_price_span = price_span.find_next_sibling('span')

        if old_price_span:
            old_price_content = old_price_span.text.strip().replace('S/', '').replace(',', '').strip()
            pvp = float(old_price_content)
        else:
            pvp = pvp_internet

        pvp_internet = pvp_internet if pvp_internet != pvp else None
        image = urllib.parse.quote(html.find(id='img-detail').find('a', class_='imagezoom').get('href').replace('https://', '').strip())

        # Getting categories
        breadcrumbs = []
        breadcrumb_list = html.find('ul', class_='breadcrumb').find_all('li')

        for breadcrumb in breadcrumb_list:
            if breadcrumb.a is not None:
                breadcrumbs.append(Utils.proc_name(breadcrumb.a.text))

        if len(breadcrumbs) > 1:
            breadcrumbs = breadcrumbs[1:len(breadcrumbs) - 1]

        product['product_id'] = hashlib.sha256(link.encode()).hexdigest()
        product['product_code'] = None
        product['sku'] = None
        product['url'] = link
        product['provider'] = provider
        product['brand'] = brand
        product['model'] = model
        product['category'] = " -- ".join(breadcrumbs) if len(breadcrumbs) > 0 else category
        product['name'] = Utils.proc_name(name.text)
        product['description'] = None
        product['technical_specs'] = " -- ".join(specs) if len(specs) > 0 else None
        product['pvp'] = pvp
        product['pvp_internet'] = pvp_internet
        product['pvp_discount'] = -1
        product['amount_sold'] = -1
        product['amount_available'] = -1
        product['img'] = "https://{}".format(image)
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


UnaLuka().run()
