# Create model to be inserte into the database
from logger.log import Log


class ProviderItem:
    product_id = "product_id"
    url = "url"
    provider = "provider"
    name = "name"
    timestamp = "timestamp"
    time_iso = "time_iso"
    brand = "brand"
    amount_sold = "amount_sold"
    amount_available = "amount_available"
    currency = "currency"
    pvp = "pvp"
    pvp_discount = "pvp_discount"
    pvp_internet = "pvp_internet"
    category = "category"
    description = "description"
    technical_specs = "technical_specs"
    model = "model"
    img = "img"
    product_code = "product_code"
    sku = "sku"

    __fields = [url,
                provider,
                name,
                brand,
                amount_sold,
                amount_available,
                currency,
                pvp,
                pvp_internet,
                pvp_discount,
                category,
                model,
                img]

    __fields2 = [product_id,
                 product_code,
                 sku,
                 url,
                 provider,
                 brand,
                 model,
                 category,
                 name,
                 description,
                 technical_specs,
                 pvp,
                 pvp_internet,
                 pvp_discount,
                 amount_sold,
                 amount_available,
                 img,
                 timestamp,
                 time_iso]

    def to_csv(self, data: list, filename: str, separator: str = "|"):
        self.save(data, filename, self.__fields, separator)

    def to_csv2(self, data: list, filename: str, separator: str = "|"):
        self.save(data, filename, self.__fields2, separator)

    def save(self, data: list, filename: str, fields: list, separator: str = "|"):
        file_content = ""
        # Header
        file_content += separator.join(fields) + "\n"

        for item in data:

            if len(item) != len(fields):
                Log.warn(str(item) + " \n -> Has a different size than expected fields.")

            line = []

            for f in fields:
                value = item.get(f, "")
                line.append(str(value))

            file_content += separator.join(line) + "\n"

        file = open(filename + ".csv", 'a+')
        file.write(file_content)
        # Closing file
        file.flush()
        file.close()
