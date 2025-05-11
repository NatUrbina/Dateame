from database.model.hand_matching import hand_matches
from database.model.model import ProviderItem


class Matcher:
    codes = {}
    size = 0

    def match(self, item):
        key = item[ProviderItem.category].lower().replace(" ", "") + \
              item[ProviderItem.brand].lower().replace(" ", "").replace("Otros", "") + \
              item[ProviderItem.model].lower().replace(" ", "").replace("Otros", "")

        item_code = self.codes.get(key, None)
        if item_code is None:
            self.size += 1
            self.codes[key] = self.size
            item_code = self.size

        for k, v in hand_matches.items():
            if item[ProviderItem.url] in v:
                print(item[ProviderItem.url])
                print(int(k))
                return int(k)

        return item_code
