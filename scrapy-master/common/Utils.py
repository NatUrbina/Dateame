import unidecode
import pytz
from datetime import datetime


class Utils:

    @staticmethod
    def proc_category(category):
        category = unidecode.unidecode(category).lower() if category is not None else 'otros'
        category = category if '.' not in category else 'otros'

        if '--' in category:
            parts = category.split('--')
            category = parts[len(parts) - 1].strip()

        return category

    @staticmethod
    def proc_name(name):
        return ' '.join(unidecode.unidecode(name.replace('|', '').replace("\n", '')).split())

    @staticmethod
    def proc_price(pvp):
        pvp = pvp.replace('S/', '').replace(',', '').replace("\n", '').replace('No disponible', '-2').replace('599 Internet', '').replace('Internet', '').replace('1-1', '').replace('lower', '').strip()
        pvp = -1 if pvp == '' or pvp == 'None' else float(pvp)
        return pvp

    @staticmethod
    def proc_amount(amount):
        return -1 if amount == '' or amount == 'None' else float(amount)

    @staticmethod
    def get_current_date():
        date = datetime.now(pytz.utc)
        timestamp = int(datetime.timestamp(date))
        dateiso = date.isoformat().split('.')[0]

        return timestamp, dateiso

    @staticmethod
    def get_brand_model(category):
        if "audio" == category.lower():
            return "audio"
        elif "cámaras" == category.lower():
            return "camaras"
        elif "celulares & smartwatch" == category.lower():
            return "smartphones"
        elif "cómputo" == category.lower():
            return "computacion"
        elif "gaming" == category.lower():
            return "gaming"
        elif "navajas" == category.lower():
            return "navajas"
        elif "moda" == category.lower():
            return "moda"

        return "otros"
