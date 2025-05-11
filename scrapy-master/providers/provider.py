from driver.chrome import ChromeDriver


class Provider:
    driver = None

    def __init__(self):
        self.driver = ChromeDriver()

    @staticmethod
    def get_item(html):
        raise NotImplemented

    @staticmethod
    def get_urls(html):
        raise NotImplemented

    @staticmethod
    def has_more_pages(html):
        raise NotImplemented

    def test_get_item(self, url, wait_conditions=()):
        html = self.driver.get(url, wait_conditions)
        return self.get_item(html)
