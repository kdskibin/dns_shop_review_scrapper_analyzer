"""Обработка текстов отзывов: разделение, препроцессинг, лемматизация, стоп-слова."""
import re
import nltk
from pymystem3 import Mystem


def convert_to_list_of_reviews(reviews: list[dict], review_len_threshold: int) -> list[str]:
    """
    Преобразует список словарей (отзывов) в список строк,
    где каждая строка - объединение частей отзыва.

    Parameters
    ----------
    reviews : list[dict]
        Список словарей с отзывами, полученных парсером.
    review_len_threshold : int
        Минимальная длина части (по количеству слов), чтобы она была включена в результат.

    Returns
    -------
    list[str]
        Список строк, каждая из которых содержит объединенные фрагменты отзыва.
    """
    dict_of_none = {'Достоинства' : None, 'Недостатки' : None, 'Комментарий' : None, 'Фото' : None}
    texts = []
    for review in reviews:
        if review != dict_of_none:
            texts.append('')  # Если все значения в review - None, но есть ключа нет в dict_of_none, происходит утечка памяти. Нужно исправить
            for key, value in review.items():
                if (value is not None) and (key in dict_of_none.keys()) and (len(value.split(' ')) > review_len_threshold):
                    texts[-1] += ' ' + value + ' '
    return texts


def split_positive_negative_parts(reviews: list[dict], review_min_len_threshold: int) -> tuple[list[str], list[str]]:
    """
    Делит отзывы на положительные и отрицательные части.

    Parameters
    ----------
    reviews : list[dict]
        Список словарей с отзывами.
    review_min_len_threshold : int
        Минимальная длина фразы (по количеству слов), чтобы она попала в результат.

    Returns
    -------
    tuple[list[str], list[str]]
        Позиция 0 – список положительных фраз,
        позиция 1 – список отрицательных фраз.
    """
    dict_of_none = {'Достоинства' : None, 'Недостатки' : None, 'Комментарий' : None, 'Фото' : None}
    positive_list = []
    negative_list = []
    for review in reviews:
        if review != dict_of_none:
            for key, value in review.items():
                if (value is not None) and (len(value.split(' ')) > review_min_len_threshold):
                    if key == 'Достоинства':
                        positive_list.append(value)
                    elif key == 'Недостатки':
                        negative_list.append(value)
                    else:
                        break
    return (positive_list, negative_list)


def preprocess_list_of_texts(list_of_texts: list[str], to_lower: bool, erase_punct: bool) -> list[str]:
    """
    Выполняет базовый препроцессинг текста.

    Parameters
    ----------
    list_of_texts : list[str]
        Список исходных строк.
    to_lower : bool
        Если True – переводит все символы в нижний регистр.
    erase_punct : bool
        Если True – удаляет пунктуацию, заменяя ее пробелом.

    Returns
    -------
    list[str]
        Препроцессированные строки.
    """
    cleaned_list = []
    for idx, text in enumerate(list_of_texts):
        cleaned_list.append(text.lower() if to_lower else text)
        if erase_punct:
            cleaned_list[idx] = re.sub(r'[^\w\s]', ' ', cleaned_list[idx])
        cleaned_list[idx] = re.sub(r'\s+', ' ', cleaned_list[idx])
    return cleaned_list


# Возможность предварительной лемматизации отзывов перед извлечением ключевых N-грамм
def lemmatize_texts(list_of_texts: list[str], mystem: Mystem) -> list[str]:
    """
    Лемматизирует список строк с помощью pymystem3.

    Parameters
    ----------
    list_of_texts : list[str]
        Список исходных строк.
    mystem : Mystem
        Экземпляр класса лемматизации.

    Returns
    -------
    list[str]
        Список лемматизированных строк.
    """
    separator = '!@#$%^&*()'
    lemmatized_text = ''.join(mystem.lemmatize(separator.join(list_of_texts)))
    lemmatized_list = lemmatized_text.split(separator)
    return lemmatized_list


def delete_stop_words(list_of_texts: list[str], language: str, allowed_stopwords: list[str]=None) -> list[str]:
    """
    Удаляет стоп‑слова из списка строк.

    Parameters
    ----------
    list_of_texts : list[str]
        Список исходных строк.
    language : str, optional
        Язык для набора стоп‑слов (по умолчанию «russian»).
    allowed_stopwords : list[str] | None, optional
        Допустимые слова, которые не будут удалены даже если они входят в стоп‑слова.

    Returns
    -------
    list[str]
        Список строк без стоп‑слов.
    """
    stopwords = nltk.corpus.stopwords.words(language)

    list_of_tokens = []
    for text in list_of_texts:
        list_of_tokens.append(nltk.tokenize.word_tokenize(text, language=language))
    cleaned_corpus_list = []
    for review_tokens in list_of_tokens:
        cleaned_corpus = []
        for token in review_tokens:
            if (token not in stopwords) or (token in allowed_stopwords):
                cleaned_corpus.append(token)
        cleaned_corpus_list.append(' '.join(cleaned_corpus))
    return cleaned_corpus_list