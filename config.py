import os

"""Конфигурация приложения: пути, параметры парсера, анализатора и генератора облака слов."""

class Config:
    """
    Единый источник конфигурации приложения.

    Группы параметров
    -----------------
    Пути: директории и файлы данных, cookies, JSON, raw HTML, статика.
    Парсер: границы задержек, минимальное и максимальное количество отзывов.
    Пул парсеров: размер пула, режим блокировки, таймаут.
    Браузер: headless-режим, количество попыток открытия сайта.
    Анализ: регистр, порог длины, язык, пунктуация, параметры KeyBERT, разрешенные стоп-слова.
    WordCloud: размеры, фон, цветовая схема, состояние генератора случайных чисел.
    """

    USE_PREPARED = True  # Использовать подготовленный HTML вместо парсинга

    # Пути
    DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
    COOKIES_PATH = os.path.join(DATA_DIR, 'cookies.pkl')
    REVIEWS_JSON_PATH = os.path.join(DATA_DIR, 'reviews.json')
    RAW_HTML_PATH = os.path.join(DATA_DIR, 'raw_html.txt')
    STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')
    POSITIVE_IMAGE_PATH = os.path.join(STATIC_DIR, 'positive.png')
    NEGATIVE_IMAGE_PATH = os.path.join(STATIC_DIR, 'negative.png')

    # Парсер
    PARSER_WAITING_TIME_LB = 4  # Нижняя граница задержки перед действием в браузере (сек.)
    PARSER_WAITING_TIME_UB = 6  # Верхняя граница задержки (сек.)
    PARSER_REVIEWS_LB = 10  # Минимальное желаемое количество отзывов
    PARSER_REVIEWS_UB = 400  # Максимальное желаемое количество отзывов

    # Пул парсеров
    PARSER_POOL_SIZE = 2  # Размер пула парсеров
    PARSER_POOL_BLOCK = True  # Блокировать операции get/put до таймаута
    PARSER_POOL_TIMEOUT = 5  # Время ожидания операций get/put (сек.)

    # Браузер
    BROWSER_HEADLESS = False  # Запускать браузер в режиме без интерфейса
    BROWSER_CITE_OPENING_ATTEMPTS = 2  # Количество попыток открытия сайта при ошибке 403

    # Анализ
    ANALYZER_TO_LOWERCASE = True  # Приводить текст к нижнему регистру
    ANALYZER_MIN_REVIEW_LEN_THRESHOLD = 5  # Минимальная длина отзыва (кол-во слов)
    ANALYZER_LANGUAGE = 'russian'  # Язык стоп-слов
    ANALYZER_ERASE_PUNCTUATION = False  # Удалять пунктуацию из текста
    ANALYZER_TOP_N_KEYWORDS = 2  # Количество извлекаемых ключевых фраз на отзыв
    ANALYZER_CONFIDENCE_THRESHOLD = 0.5  # Порог косинусного сходства ключевой фразы
    ANALYZER_KEYPHRASE_NGRAM_RANGE = (2, 3)  # Диапазон длин n-грамм (мин., макс.)
    # ANALYZER_KEYBERT_MODEL_NAME = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'  # Плохое качество ключевых фраз
    ANALYZER_KEYBERT_MODEL_NAME = 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2'  # Модель KeyBERT
    ANALYZER_KEYBERT_DIVERSITY = 0.7  # Разнообразие ключевых фраз: чем выше, тем разнообразнее фразы
    ANALYZER_ALLOWED_STOPWORDS = ['не', 'ни', 'но']  # Стоп-слова, которые не будут удаляться

    # WordCloud
    WORDCLOUD_WIDTH = 1000  # Ширина изображения (пкс)
    WORDCLOUD_HEIGHT = 1000  # Высота изображения (пкс)
    WORDCLOUD_BACKGROUND_COLOR = 'black'  # Цвет фона
    WORDCLOUD_COLORMAP = 'Pastel1'  # Цветовая схема
    WORDCLOUD_RANDOM_STATE = 42  # Seed генератора случайных чисел
    WORDCLOUD_COLLOCATIONS = True  # Использовать n-граммы в облаке слов
    WORDCLOUD_MARGIN = 20  # Отступ изображения (пкс) 