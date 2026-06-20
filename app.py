"""Flask-приложение для сбора и анализа отзывов с dns-shop.ru.

Пайплайн: парсинг отзывов через Selenium -> разделение на позитив/негатив ->
препроцессинг текста -> извлечение ключевых фраз KeyBERT -> генерация облаков слов.
"""

from dotenv import load_dotenv
from config import Config

load_dotenv("./.env", override=True) # HF_HOME, HF_TOKEN

from flask import Flask, url_for, render_template, request, redirect
from scripts import error_codes_dict
from scripts.parser_pool import ParserPool
from keybert import KeyBERT
import scripts.text_processing as tp
import scripts.analyzer as text_analyzer
from scripts.vizualizer import WordCloudGenerator
from pymystem3 import Mystem
import nltk
import time

# Done TODO: Инициализация модели для анализа происходит только один раз, при запуске приложения
# Done TODO: Пул парсеров (объектов DNS_Shop_Parser), а не создание нового при каждом запросе
# TODO: Улучшить качество ключевых фраз, извлекаемых из отзывов
# TODO: Ротация IP адресов

app = Flask(__name__, template_folder='templates')

keybert_model = KeyBERT(Config.ANALYZER_KEYBERT_MODEL_NAME)

parser_pool = ParserPool(size=Config.PARSER_POOL_SIZE, block=Config.PARSER_POOL_BLOCK,
                         timeout=Config.PARSER_POOL_TIMEOUT, browser_headless=Config.BROWSER_HEADLESS)

mystem = Mystem()

nltk.download('punkt')
nltk.download('stopwords')
nltk.download('punkt_tab')


@app.route('/', methods=['GET', 'POST'])
def index():
    """Главная страница – форма ввода URL и количества отзывов."""
    if request.method == 'POST':
        review_url = request.form['review_url']
        review_cnt = int(request.form['review_cnt'])
        return redirect(url_for('analyzing', review_url=review_url, review_cnt=review_cnt))
    else:
        return render_template(
            'index.html',
            min_reviews_value=Config.PARSER_REVIEWS_LB,
            max_review_value=Config.PARSER_REVIEWS_UB
        )


@app.route('/analyzing', methods=['GET'])
def analyzing():
    """Получает URL и количество отзывов из GET-параметров, запускает анализ и возвращает страницу результатов или ошибку."""
    review_url = request.args.get('review_url')
    review_cnt = int(request.args.get('review_cnt'))
    parser = parser_pool.get()
    response = _analyze_product(parser, review_url, review_cnt)
    put_result = parser_pool.put(parser)

    if put_result is None:
        return render_template('error.html', error_cause=error_codes_dict[521])
    return response


def _analyze_product(parser, review_url, review_cnt):
    """
    Выполняет полный пайплайн анализа отзывов и возвращает HTTP-ответ.

    Parameters
    ----------
    parser : DNS_Shop_Parser | None
        Парсер из пула. Если None — вернет страницу ошибки.
    review_url : str | None
        URL страницы отзывов товара. Если None — вернет страницу ошибки.
    review_cnt : int
        Желаемое количество отзывов для загрузки.

    Returns
    -------
    flask.Response
        Страница результатов (results.html) или страница ошибки (error.html).
    """
    try:
        if not Config.USE_PREPARED:
            start_time = time.time()
            if not parser.successful_open:
                parser.open_DNS_site(attempts=Config.BROWSER_CITE_OPENING_ATTEMPTS)
            reviews = parser.get_product_reviews(review_url, review_cnt, Config.BROWSER_CITE_OPENING_ATTEMPTS)
            end_time = time.time()
            print('extract_reviews execution_time ', end_time - start_time)
        else:
            start_time = time.time()
            reviews = []
            with open(Config.RAW_HTML_PATH, 'r', encoding='utf-8') as file:
                reviews = parser.extract_reviews(file.read())
            end_time = time.time()
            print('extract_reviews execution_time ', end_time - start_time)

        start_time = time.time()
        positive_list, negative_list = tp.split_positive_negative_parts(
            reviews, Config.ANALYZER_MIN_REVIEW_LEN_THRESHOLD
        )
        end_time = time.time()
        print('split_positive_negative_parts execution_time ', end_time - start_time)

        start_time = time.time()
        positive_list = tp.preprocess_list_of_texts(
            positive_list, to_lower=Config.ANALYZER_TO_LOWERCASE,
            erase_punct=Config.ANALYZER_ERASE_PUNCTUATION
        )
        negative_list = tp.preprocess_list_of_texts(
            negative_list, to_lower=Config.ANALYZER_TO_LOWERCASE,
            erase_punct=Config.ANALYZER_ERASE_PUNCTUATION
        )
        end_time = time.time()
        print('preprocess_list_of_texts execution_time ', end_time - start_time)

        # start_time = time.time()
        # positive_list, negative_list = (tp.lemmatize_texts(positive_list, mystem), tp.lemmatize_texts(negative_list, mystem))
        # end_time = time.time()
        # print('lemmatize_texts execution_time ', end_time-start_time)

        start_time = time.time()
        positive_list, negative_list = (tp.delete_stop_words(positive_list, Config.ANALYZER_LANGUAGE, Config.ANALYZER_ALLOWED_STOPWORDS),
                                        tp.delete_stop_words(negative_list, Config.ANALYZER_LANGUAGE, Config.ANALYZER_ALLOWED_STOPWORDS))
        end_time = time.time()
        print('delete_stop_words execution_time ', end_time-start_time)

        start_time = time.time()
        positive_raw_keywords_list = text_analyzer.extract_keyphrases(positive_list, keybert_model,
                                                                      Config.ANALYZER_TOP_N_KEYWORDS,
                                                                      Config.ANALYZER_KEYPHRASE_NGRAM_RANGE,
                                                                      Config.ANALYZER_KEYBERT_DIVERSITY)
        negative_raw_keywords_list = text_analyzer.extract_keyphrases(negative_list, keybert_model,
                                                                      Config.ANALYZER_TOP_N_KEYWORDS,
                                                                      Config.ANALYZER_KEYPHRASE_NGRAM_RANGE,
                                                                      Config.ANALYZER_KEYBERT_DIVERSITY)
        end_time = time.time()
        print('extract_keyphrases execution_time ', end_time-start_time)

        start_time = time.time()
        positive_keywords_dict = text_analyzer.get_dict_keyphrases(positive_raw_keywords_list, threshold=Config.ANALYZER_CONFIDENCE_THRESHOLD)
        negative_keywords_dict = text_analyzer.get_dict_keyphrases(negative_raw_keywords_list, threshold=Config.ANALYZER_CONFIDENCE_THRESHOLD)
        end_time = time.time()
        print('get_dict_keyphrases execution_time ', end_time-start_time)

        WordCloudGenerator.generate(positive_keywords_dict, Config.POSITIVE_IMAGE_PATH, save_image=True)
        WordCloudGenerator.generate(negative_keywords_dict, Config.NEGATIVE_IMAGE_PATH, save_image=True)

    except Exception as ex:
        app.logger.exception('Ошибка при анализе: %s', ex)
        return render_template('error.html', error_cause=error_codes_dict[1])

    return render_template('results.html',
                           positive_img_src='static/positive.png',
                           negative_img_src='static/negative.png')

  
@app.route('/results', methods=['GET'])
def results():
    """Страница отображения результатов — рендерит облака слов для позитивных и негативных отзывов."""
    return render_template('results.html',
                           positive_img_src='static/positive.png',
                           negative_img_src='static/negative.png')


@app.route('/error', methods=['GET'])
def error():
    """Страница обработки ошибок. Принимает код ошибки из query-параметра 'code'."""
    error_code = request.args.get('code')
    if error_code in error_codes_dict:
        return render_template('error.html', error_cause=error_codes_dict[error_code])
    else:
        return render_template('error.html', error_cause=error_codes_dict[1])

if __name__ == "__main__":
    # app.run(host='0.0.0.0', port=42960, debug=False)
    app.run(debug=True)