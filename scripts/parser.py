"""Модуль для парсинга отзывов с dns-shop.ru.

Использует Selenium + undetected_chromedriver для обхода защиты DNS,
BeautifulSoup для парсинга HTML, и JSON для сериализации cookies.
"""
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from config import Config
import random
import time
import os.path
import json

# TODO: имитация человеческого поведения при действиях

WAITING_TIME_LB, WAITING_TIME_UB = (Config.PARSER_WAITING_TIME_LB, Config.PARSER_WAITING_TIME_UB)

class BrowserManager:
    """
    Упрощенный обертка над undetected_chromedriver.

    Attributes
    ----------
    browser : uc.Chrome
        Экземпляр браузера, который используется для всех операций.
    """
    def __init__(self, headless: bool):
        """
        Инициализация экземпляра BrowserManager.

        Параметры
        ---------
        headless : bool
            Если True – открывать браузер в режиме «headless» (без UI).
        """
        self.browser = uc.Chrome(headless=headless)
        self.browser.implicitly_wait(5)
        self.browser.maximize_window()
        time.sleep(random.randint(Config.PARSER_WAITING_TIME_LB, Config.PARSER_WAITING_TIME_UB))


    def _change_main_window(self):
        """
        Переключает фокус на главное окно браузера.
        Если открыто несколько вкладок, переключается к той,
        которая не является «основной».
        """
        if len(self.browser.window_handles) > 1:
            original_window = self.browser.current_window_handle
            for window_handle in self.browser.window_handles:
                if window_handle != original_window:
                    self.browser.switch_to.window(window_handle)
                    break


    def _close_excess_windows(self):
        """
        Закрывает все лишние вкладки, оставляя только главную.
        """
        if len(self.browser.window_handles) > 1:
            original_window = self.browser.current_window_handle
            for window_handle in self.browser.window_handles:
                if window_handle != original_window:
                    self.browser.switch_to.window(window_handle)
                    self.browser.close()
                    self.browser.switch_to.window(original_window)


    def write_cookies(self, filename: str):
        """
        Сохраняет cookies текущей сессии в JSON-файл.

        Parameters
        ----------
        filename : str
            Путь к файлу, куда будут записаны cookies.
        """
        cookies = self.browser.get_cookies()
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(cookies, file)


    def read_cookies(self, filename: str):
        """
        Загружает cookies из JSON-файла и добавляет их в текущую сессию.

        Parameters
        ----------
        filename : str
            Путь к файлу с cookies.
        """
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as file:
                cookies = json.load(file)
                for cookie in cookies:
                    self.browser.add_cookie(cookie)


    def __del__(self) -> None:  # pragma: no cover
        """
        Закрывает браузер при удалении объекта.
        """
        self.browser.quit()


class NavigationManager:
    """
    Упрощенный менеджер навигации, скрывающий детали работы с Selenium.

    Parameters
    ----------
    browser : BrowserManager
        Экземпляр BrowserManager, через который осуществляется взаимодействие.
    """
    def __init__(self, browser: BrowserManager):
        """
        Инициализация NavigationManager.

        Параметры
        ---------
        browser : BrowserManager
            Управляющий объект браузера.
        """
        self.browser_manager = browser


    def _handle_403_error(self):
        """
        При возникновении ошибки 403 открывает новую вкладку с https://ya.ru,
        переключается на нее и закрывает все лишние окна.
        """
        self.browser_manager.browser.execute_script('''window.open("https://ya.ru","_blank");''')
        self.browser_manager._change_main_window()
        time.sleep(random.randint(WAITING_TIME_LB, WAITING_TIME_UB))
        self.browser_manager._close_excess_windows()


    # Вводит запрос в поисковую строку Яндекса
    def _enter_query(self, query:str):
        """
        Вводит поисковый запрос в поле поиска Яндекс.

        Parameters
        ----------
        query : str
            Текст запроса.
        """
        search = self.browser_manager.browser.find_element(By.ID, "text")
        search.clear()
        search.send_keys(query)
        time.sleep(random.randint(WAITING_TIME_LB, WAITING_TIME_UB))
        search.send_keys(Keys.RETURN)


    # GET-запрос с обработкой ошибки 403
    def try_open_page(self, url:str, attempts:int):
        """
        Пытается открыть страницу по URL с заданным числом попыток.

        Parameters
        ----------
        url : str
            Адрес страницы.
        attempts : int
            Максимальное число попыток.

        Returns
        -------
        bool
            True – если страница открылась успешно, False – иначе.
        """
        for i in range(attempts):
            self.browser_manager.browser.get(url)
            # При ошибке 403 пробуем открыть новую вкладку
            if 'HTTP 403' in self.browser_manager.browser.page_source:
                if i == attempts-1:
                    print('Не удалось открыть страницу за указанное число попыток')
                    return False
                print(f'Ошибка 403. Пробуем открыть ссылку в другой вкладке. Попытка {i+1}')
                self._handle_403_error()
                time.sleep(random.randint(WAITING_TIME_LB, WAITING_TIME_UB))
            else:
                return True


    # Открытие сайта через поиск Яндекса для получения cookie и обхода проверки на бота
    def try_open_page_via_search(self, search_query:str, url_part:str, attempts:int):
        """
        Открывает страницу по URL, предварительно найдя ее в поиске Яндекса.
        Это помогает обойти проверку на наличие cookie.

        Parameters
        ----------
        search_query : str
            Текст для поиска (например, «днс»).
        url_part : str
            Фрагмент адреса сайта, который нужно найти в результатах поиска
            (например, «dns-shop.ru»).
        attempts : int
            Максимальное число попыток.

        Returns
        -------
        bool
            True – если страница открылась успешно, False – иначе.
        """
        for i in range(attempts):
            self.browser_manager.browser.get('https://ya.ru')
            time.sleep(random.randint(WAITING_TIME_LB, WAITING_TIME_UB))
            try:
                self._enter_query(search_query)
                time.sleep(random.randint(WAITING_TIME_LB, WAITING_TIME_UB))

                # Кнопка закрытия всплывающих подсказок
                notification_close_button = WebDriverWait(self.browser_manager.browser, 8).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.Distribution-ButtonClose')))
                notification_close_button.click()
                time.sleep(random.randint(WAITING_TIME_LB, WAITING_TIME_UB))

                # Поиск ссылки, содержащей url_part
                link = self.browser_manager.browser.find_element(By.PARTIAL_LINK_TEXT, url_part)
                time.sleep(random.randint(WAITING_TIME_LB, WAITING_TIME_UB))
                link.click()
                self.browser_manager._change_main_window()
                time.sleep(random.randint(WAITING_TIME_LB, WAITING_TIME_UB))
                self.browser_manager._close_excess_windows()
            except Exception:
                print('Не удалось найти интерактивный элемент :(')
            
            # Обработка ошибки 403: открытие новой вкладки
            if 'HTTP 403' in self.browser_manager.browser.page_source:
                if i == attempts-1:
                    print('Не удалось открыть страницу за указанное число попыток')
                    return False
                print(f'Ошибка 403. Пробуем открыть ссылку в другой вкладке. Попытка {i+1}')
                self._handle_403_error()
                time.sleep(random.randint(WAITING_TIME_LB, WAITING_TIME_UB))
            else:
                return True


class ParseHelper:
    """
    Утилита для работы с содержимым открытой страницы.

    Parameters
    ----------
    browser : BrowserManager
        Экземпляр BrowserManager, через который можно получить html‑код.
    """
    def __init__(self, browser: BrowserManager):
        """
        Инициализация ParseHelper.

        Параметры
        ---------
        browser : BrowserManager
            Управляющий объект браузера.
        """
        self.browser_manager = browser


    def get_page_raw_html(self) -> str:
        """
        Возвращает сырой HTML-код открытой страницы.

        Returns
        -------
        str
            Строка с полным html‑кодом.
        """
        return self.browser_manager.browser.page_source


    def page_to_txt(self, file_name:str):
        """
        Сохраняет raw‑html в файл.

        Parameters
        ----------
        file_name : str
            Путь к файлу, куда будет записан html‑код.
        """
        with open(file_name, 'w', encoding='utf-8') as file:
            raw_html = self.get_page_raw_html()
            file.write(raw_html)


class DNS_Shop_Parser:
    """
    Парсер отзывов с сайта dns-shop.ru.

    Использует Selenium для автоматизации браузера, обходит защиту от ботов
    через поиск в Яндексе. Извлекает достоинства, недостатки и комментарии
    покупателей из HTML-страницы отзывов.

    Parameters
    ----------
    headless : bool
        Если True – браузер запускается в режиме без UI.
    """
    def __init__(self, headless: bool):
        """
        Инициализация парсера: создает браузер, навигатор и помощник парсинга.
        """
        self.browser_manager = BrowserManager(headless=headless)
        self.navigator = NavigationManager(self.browser_manager)
        self.parse_helper = ParseHelper(self.browser_manager)
        self.successful_open = False


    def how_to_use(self):
        """
        Возвращает краткую инструкцию по использованию парсера.
        """
        return '''
                1. Создайте экземпляр парсера DNS_Shop_Parser (это уже сделано)
                2. Используйте метод /.open_DNS_site()/ для обхода защиты от ботов
                3.1. Используйте метод /.get_product_reviews('url_отзывов')/ для получения отзывов списком словарей
                3.2. Используйте метод /parse_helper.page_to_txt()/ для сохранения HTML в .txt файл'''


    # Работает только со страницей отзывов товара
    def show_more_reviews(self, desired_review_cnt: int):
        """
        Кликает кнопку «Показать еще», пока не будет загружено нужное количество отзывов.

        Каждое нажатие загружает 10 отзывов, изначально отображается 4.

        Parameters
        ----------
        desired_review_cnt : int
            Желаемое количество отзывов на странице.

        Returns
        -------
        None
        """
        button_click_cnt = (desired_review_cnt-4)//10 + 1  # Каждое нажатие загружает 10 отзывов, изначально показано 4
        for _ in range(button_click_cnt):
            time.sleep(random.randint(WAITING_TIME_LB, WAITING_TIME_UB))
            try:
                # show_more_button = self.browser_manager.browser.find_element(By.CSS_SELECTOR, "button.paginator-widget__more")
                show_more_button = WebDriverWait(self.browser_manager.browser, 8).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.paginator-widget__more')))
                show_more_button.click()
            except Exception:
                print('Не удалось загрузить нужное количество отзывов')


    def extract_reviews(self, raw_html: str) -> list[dict]:
        """
        Извлекает отзывы из html‑страницы.

        Parameters
        ----------
        raw_html : str
            Сырой HTML-код страницы с отзывами.

        Returns
        -------
        list[dict]
            Список словарей, где каждый элемент представляет один отзыв.
            Ключи: 'Достоинства', 'Недостатки', 'Комментарий', 'Фото'.
        """
        soup = BeautifulSoup(raw_html, 'html.parser')
        # Поиск всех отзывов на странице (зависит от структуры HTML DNS)
        # 'ow-opinion__texts' содержит заголовки (Достоинства, Недостатки, ...) и блоки комментариев
        all_reviews = soup.find_all('div', 'ow-opinion__texts', recursive=True)
        parsed_reviews = []
        for review in all_reviews:
            title_part = review.find_all('div', 'ow-opinion__text-title')  # Заголовки «Достоинства» / «Недостатки»
            desc_part = review.find_all('div', 'ow-opinion__text-desc')  # Тексты комментариев
            parsed_reviews.append({'Достоинства' : None, 'Недостатки' : None, 'Комментарий' : None, 'Фото' : None})
            for el in zip(title_part, desc_part):
                parsed_reviews[-1][el[0].text] = el[1].text  # Объединяем заголовок и текст в словарь
        return parsed_reviews  # Список словарей, где каждый элемент — один отзыв
    

    def open_DNS_site(self, attempts: int):
        """
        Пытается открыть главную страницу dns-shop.ru через поиск Яндекса.
        При успехе устанавливает `self.successful_open = True`.

        Parameters
        ----------
        attempts : int
            Максимальное число попыток открытия.

        Returns
        -------
        None
        """
        if self.navigator.try_open_page_via_search('днс', 'dns-shop.ru', attempts=attempts):
            self.successful_open=True


    def get_product_reviews(self, url_review_page: str, desired_review_cnt: int, attempts: int):
        """
        Загружает страницу с отзывами и возвращает список отзывов.

        Parameters
        ----------
        url_review_page : str
            URL страницы с отзывами конкретного товара.
        desired_review_cnt : int
            Желаемое число отзывов для загрузки.

        Returns
        -------
        list[dict]
            Список словарей с отзывами, полученный функцией `extract_reviews`.
        """
        self.navigator.try_open_page(url_review_page, attempts=attempts)
        self.show_more_reviews(desired_review_cnt)
        raw_html = self.parse_helper.get_page_raw_html()
        return self.extract_reviews(raw_html)
    
__all__ = ['DNS_Shop_Parser']