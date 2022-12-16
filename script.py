import os
import re
import string
import requests
import json
from selenium import webdriver, common
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from webdriver_manager.chrome import ChromeDriverManager


class Parser:
    def __init__(self, login, password, depth, threshold):
        self.login = login
        self.password = password
        self.depth = depth
        self.threshold = threshold
        options = webdriver.ChromeOptions()
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        self._R = webdriver.Chrome(options=options, service=Service(
            ChromeDriverManager().install()))
        self.__log_in()
        self._pattern = r'[' + string.punctuation + ']'

    def __log_in(self):
        self._get('https://vk.com/login')
        username = self.__wait('VkIdForm__input')
        username.send_keys(self.login)

        button = self._R.find_element(By.CLASS_NAME, 'VkIdForm__signInButton')
        button.click()

        password_wrapper = self.__wait("vkc__Password__Wrapper", time=90)
        password = password_wrapper.find_element(
            By.CLASS_NAME, "vkc__TextField__input")
        password.send_keys(self.password)

        button_wrapper = self.__wait(
            "vkc__EnterPasswordNoUserInfo__buttonWrap")
        button = button_wrapper.find_element(By.CLASS_NAME, "vkuiButton")
        button.click()

        self.__wait_all("page_layout", id=True)

    def parse_groups(self, ids):
        for id in ids:
            self._parse_group(id)

    def _parse_group(self, id):
        url = f'https://m.vk.com/{id}?donut=1#wall'
        self._get(url)
        for i in range(self.depth):
            self.__wait_all("posts_container", id=True)
            self._R.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);")
        try:
            return self.__wait("DonutWallAlert", 0.5)
        except common.exceptions.TimeoutException:
            pass
        articles = self.__wait_all("articleSnippet__block")
        links = []
        for article in articles:
            links.append(article.get_property("href"))
        for link in links:
            self._parse_article(link)

    def _parse_article(self, url):
        self._get(url)
        self.__wait("vk__page")
        images = self.__wait_all("article_object_sizer_inner")
        for image in images:
            self._R.execute_script(
                f"window.scrollBy(0, document.body.scrollHeight / {len(images)})")
            size = [image.get_attribute(
                'naturalWidth'), image.get_attribute('naturalHeight')]
            while (self.threshold > int(size[0]) or self.threshold > int(size[1])):
                self._R.execute_script(
                    f"window.scrollBy(0, {size[1]})")
                size = [image.get_attribute(
                    'naturalWidth'), image.get_attribute('naturalHeight')]
            self._download_image(image, self._R.title, size)

    def _download_image(self, image: WebElement, title, size):
        src = image.get_property('src').replace(
            "?size=", f"?size={size[0]}x{size[1]}&")
        alt = image.get_property('alt')
        alt = re.sub(self._pattern, '', alt)
        title = re.sub(self._pattern, '', title)
        file_type = src.split(".")[3].split("?")[0]
        r = requests.get(src, allow_redirects=True)
        path = os.path.abspath(
            f"mangas/{title}/{alt}.{file_type}")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, 'wb').write(r.content)

        print(alt)
        print(src)

    def _get(self, url):
        self._R.get(url)

    def __wait(self, elem_, time=15):
        return WebDriverWait(self._R, time).until(
            EC.presence_of_element_located((By.CLASS_NAME, elem_)))

    def __wait_all(self, elem_, time=30, id=False):
        if id:
            return WebDriverWait(self._R, time).until(
                EC.presence_of_all_elements_located((By.ID, elem_)))
        return WebDriverWait(self._R, time).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, elem_)))


def main():
    config = json.load(open("config.json"))
    login, password, depth, threshold =\
        config["login"], config["password"], config["depth"], config["pixel_threshold"]
    groups = open("groups.txt", "r").readlines()

    parser = Parser(login, password, depth, threshold)
    parser.parse_groups(groups)
    input("Готово. Нажмите enter чтобы закрыть...")


main()
