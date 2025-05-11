import time

import selenium
from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By


class ChromeDriver:
    driver = None

    def __init__(self):
        super().__init__()
        options = selenium.webdriver.ChromeOptions()
        options.add_argument('headless')

        # driver_path = "./bin/linux/chromedriver"
        driver_path = "D:\\__Projects\\Dateme.pe\\scrapy\\driver\\bin\\windows\\chromedriver.exe"
        self.driver = webdriver.Chrome(chrome_options=options,
                                       executable_path=driver_path)

    def quit(self):
        self.driver.quit()

    def get(self, url, wait=()):
        self.driver.get(url)
        return self.get_source(wait)

    def get_source(self, wait=()):
        for condition in wait:
            WebDriverWait(self.driver, 60) \
                .until(self.__get_wait_condition(condition))

        return BeautifulSoup(self.driver.page_source, "html5lib")

    def hello(self):
        print("Hello i'm a chrome driver")

    def click_parent(self, element):
        button = self.driver.find_element_by_css_selector(element).find_element_by_xpath("./..")
        button.click()

    def click(self, element):
        button = self.driver.find_element_by_css_selector(element)
        button.click()

    def __get_wait_condition(self, condition):
        """
        Transforms an css selector into condition.
        :param condition: css selector
        :return: expected condition for selenium
        """
        if condition.startswith("#"):
            name = condition.replace("#", "")
            return ec.presence_of_element_located((By.ID, name))

        if condition.startswith("."):
            name = condition.replace(".", "")
            return ec.presence_of_element_located((By.CLASS_NAME, name))
