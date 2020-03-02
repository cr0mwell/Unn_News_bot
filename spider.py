import datetime
from itertools import chain
import json
import pytz
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from html.parser import HTMLParser
import os
import random
import string
import time

from class_model import (get_model, create_model, get_dataset, get_w_vectorizer, get_ch_vectorizer)
from settings import (FIREFOX_PATH, WEEKDAYS, MONTHS, COLUMNS, NUM_TO_ICONS)

# Making Firefox running in headless mode
options = Options()
options.add_argument('-headless')


class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)


def strip_tags(text):
    "Deletes html tags from the text"
    s = MLStripper()
    s.feed(text)
    return s.get_data()


def strip_accents(text, escape=False):
    """
    Removes punctuation chars from the text.
    Escapes them instead if 'escape' is set to True
    """
    for char in chain(string.punctuation, ['“', '”', '„', '–', '—', '…']):
        if escape:
            text = text.replace(char, r'\\' + char)
        else:
            text = text.replace(char, '')
    return text


def read_files(file_name):
    """
    Returns content of a json file along with the keys of its elements
    """

    with open(os.path.join('src', file_name), encoding='utf-8') as f:
        content = json.load(f)
        ids     = set(content.keys())
        return content, ids


def add_categories(driver=None):
    """
    Adds 'category' to the news stored in the src/news.json.
    """
    # Collecting the ids from the parsed news to know when it's time to stop parsing
    # Collecting file names from the fresh news available
    # Finally reading not categorized news

    print('"add_categories" operation started')

    categorized_content, categorized_article_ids = read_files('categorized_news.json')
    new_content, new_article_ids                 = read_files('news.json')
    test_content, _                              = read_files('test_news.json')

    if not driver:
        driver = webdriver.Firefox(firefox_binary=FIREFOX_PATH, options=options)

    for column in COLUMNS.keys():

        next_page = f'https://www.unn.com.ua/uk/news/{column}/page-1'

        while True:
            print(f'Parsing "{next_page}" page in {column} column')

            driver.get(next_page)
            article_ids = []

            for element in driver.find_elements_by_class_name('h-news-feed'):
                li_elems = element.find_elements_by_tag_name('li')
                for li_elem in li_elems:
                    article_id = li_elem.get_attribute('data-sort')

                    if article_id in categorized_article_ids:
                        print(f"We've reached the parsed article in '{column}' column. Exiting")
                        break

                    article_ids.append(article_id)

                else:
                    matched_ids = new_article_ids.intersection(set(article_ids))
                    if matched_ids:
                        print(f'{len(matched_ids)} matched news')

                    for id_ in matched_ids:
                        new_content[id_]['category'] = COLUMNS[column]

                    new_article_ids.difference_update(matched_ids)
                    continue

                break
            else:
                next_page = driver.find_element_by_class_name("next_page").find_element_by_tag_name("a").get_attribute("href")
                if not next_page:
                    print(f"We've reached the end of the {column} column.")
                    break

                sleep_time = random.randint(3, 10)
                time.sleep(sleep_time)
                continue
            break

    # Moving the articles that hasn't been found and categorized to test_news.json
    with open(os.path.join('src', 'test_news.json'), 'w', encoding='utf-8') as f:
        print('Updating test_news.json')
        test_content.update()
        json.dump(categorized_content, f)

    # Saving categorized news to the categorized_news.json
    new_content = {k: v for k, v in new_content.items() if k not in new_article_ids}
    categorized_content.update(new_content)

    with open(os.path.join('src', 'categorized_news.json'), 'w', encoding='utf-8') as f:
        print('Updating categorized_news.json')
        json.dump(categorized_content, f)

    # Flushing the news.json
    print('Deleting news.json')
    os.remove(os.path.join('src', 'news.json'))
    print('"add_categories" operation complete successfully')


def get_news(min_page=1, max_page=200):

    with open(os.path.join('src', 'categorized_news.json'), encoding='utf-8') as f:
        content      = json.load(f)
        last_article = max(sorted(content.keys()))

    content = {}
    driver  = webdriver.Firefox(firefox_binary=FIREFOX_PATH, options=options)

    for page in range(min_page, max_page):
        print(f'parsed {page} pages')
        driver.get('https://www.unn.com.ua/uk/news/page-%d' % page)

        links = []  # list of tuples: [(<article_id>, <article_url>),...]
        for element in driver.find_elements_by_class_name('h-news-feed'):
            li_elems = element.find_elements_by_tag_name('li')
            for li_elem in li_elems:
                article_id = li_elem.get_attribute('data-sort')

                if article_id == last_article:
                    print("We've reached the last article. Exiting")
                    break

                article_url = element.find_element_by_tag_name('a').get_attribute('href')
                links.append((article_id, article_url))

                for link in links:
                    driver.get(link[1])
                    sleep_time = random.randint(3, 10)
                    name = driver.find_element_by_class_name('title ').text

                    try:
                        article = '%s\n%s' % (strip_accents(name),
                                              '\n'.join([strip_accents(strip_tags(paragraph.text)) for paragraph in
                                                         driver.find_element_by_class_name('b-news-text ').find_elements_by_tag_name('p')]))

                        content[link[0]] = {'name': name,
                                            'text': article}

                        print(f'sleeping another {sleep_time} seconds before the next article')

                    except (StaleElementReferenceException, TimeoutException, Exception) as e:
                        print('#' * 50)
                        print(f'Exception appeared during parsing the {name} article: {e}')
                        print('skipping...')
                        print('#' * 50)

                    time.sleep(sleep_time)
            else:
                continue
            break
        else:
            continue

    with open(os.path.join('src', 'news.json'), 'w', encoding='utf-8') as f:
        json.dump(content, f)

    # Adding categories
    add_categories(driver)

    # Closing browser
    driver.quit()


def get_news_for_period(driver, period, last_article):

    cur_date = datetime.datetime.now(tz=pytz.timezone('Europe/Kiev'))

    if period == 'сьогодні':
        days = 1
    elif period == 'тиждень':
        days = cur_date.date().weekday() + 1
    else:
        days = cur_date.date().day

    border_date   = cur_date - datetime.timedelta(days=days)
    border_date   = (f'{WEEKDAYS[border_date.date().weekday()]}, '
                     f'{border_date.date().day} {MONTHS[border_date.date().month]} {border_date.date().year}')
    article_queue = {}

    if last_article is None:
        print(f'set border line as a date: "{border_date}"')
    else:
        print(f'set border line as a last_article: "{last_article}"')

    for page in range(1, 50):
        print(f'Parsing {page} page')
        driver.get(f'https://www.unn.com.ua/uk/news/page-{page}')

        date_elements = driver.find_elements_by_class_name('b-news-first-date')
        date_elements.extend(driver.find_elements_by_class_name('b-news-feed-date'))

        for date_element in date_elements:
            if date_element.text == border_date:
                print('We reached the border date')
                break

            else:
                print(f'Parsing news for {date_element.text.lower().capitalize()}')
                sleep_time = random.randint(3, 5)

                try:
                    div_elem = driver.find_element_by_xpath('//div[contains(@class, "b-news-feed-date")]//following::div[1]')
                    print(f'Found div {date_element.get_attribute("id")}')
                    li_elems = div_elem.find_elements_by_tag_name('li')

                    for li_elem in li_elems:
                        li_id = li_elem.get_attribute('data-sort')
                        if last_article == li_id:
                            print(f'We reached the last article {last_article}')
                            break

                        li_class     = li_elem.get_attribute('class')
                        article      = li_elem.find_element_by_tag_name('a')
                        article_name = article.text
                        article_link = article.get_attribute('href')

                        article_queue[li_id] = (li_class, article_name, article_link)
                    else:
                        # border element is still not found
                        continue
                    break

                except (StaleElementReferenceException, TimeoutException, Exception) as e:
                    print('#' * 50)
                    print(f'Exception appeared during parsing the {page} page: {e}')
                    print('skipping...')
                    print('#' * 50)

                print(f'sleeping another {sleep_time}sec before the next page')
                time.sleep(sleep_time)
        else:
            # border element is still not found
            continue

        print('Reached the border element. Exiting the loop')
        break
    return article_queue


def load_model_with_vetorizers():

    if not all(map(os.path.exists, [os.path.join('src', 'class_tfidf_w.vct'),
                                    os.path.join('src', 'class_tfidf_ch.vct'),
                                    os.path.join('src', 'class_model_log.md')])):
        try:
            create_model()
        except FileNotFoundError as e:
            print(f'Failed to create a new classification model: {e}')
            return None, None, None, False

    # Loading vectorizer objects, classification model
    tfidf_w  = get_w_vectorizer()
    tfidf_ch = get_ch_vectorizer()

    # Loading classification model
    class_model = get_model()

    return tfidf_w, tfidf_ch, class_model, True


def classify_text(text, vectorizers, class_model):
    "Classifies the provided text provided vectorizers and pretrained classification model."

    dataset = get_dataset([text], vectorizers)
    return class_model.predict(dataset)[0]


def parse_news(bot, uid, known_user):
    """
    Parses the news for the given period of time till the last article(if given)
    for the given columns.
    Returns obtained news in batches.

    known_user(dict) should contain the following values:
    period(str)       - one of the following values: ['сьогодні', 'тиждень', 'місяць']
    columns(set)      - one or several columns from the following:
                        ['політика', 'кримінал', 'економіка', 'світові новини', 'культура', 'добрі новини',
                         'суспільство', 'технології', 'спорт']
    last_article(str) - last sent article
    batch(int)        - number of articles to send in a batch when found
    online(bool)      - flag to indicate if the function should continue parsing
    """

    # Somekind of a lock for a user
    known_user['search_in_progress'] = True

    tfidf_w, tfidf_ch, class_model, success = load_model_with_vetorizers()
    if not success:
        print('Failed to load the classification model. Exiting')
        bot.send_message(uid, 'Виникла поилка при завантаженні класифікаційної моделі. 😔\n'
                              'Спробуй, будь ласка пізніше')
        return

    driver       = webdriver.Firefox(firefox_binary=FIREFOX_PATH, options=options)
    period       = known_user['period']
    columns      = known_user['columns']
    last_article = known_user['last_article']
    batch        = known_user['batch']
    news         = []

    # TODO: load preferences model

    while True:

        # Obtaining the fresh news
        # dict: <article_id> -> (<class>, <name>, <url>)
        article_queue = get_news_for_period(driver, period, last_article)
        news_ids      = sorted(article_queue.keys())
        if news_ids:
            print(f'Got news {news_ids[0]}-{news_ids[-1]}')

        for id_ in news_ids:
            article_class, article_name, article_url = article_queue[id_]

            # For now until the model is not predicting too accurate due to lack of training samples
            # will automatically add 'hot' news
            if article_class:
                print(f'Adding new "hot" article {(article_name, article_url)}')
                news.append(f'{NUM_TO_ICONS[9]} [{strip_accents(article_name)}]({article_url})')

            else:
                sleep_time = random.randint(3, 5)
                try:
                    driver.get(article_url)
                    content    = '%s\n%s' % (strip_accents(article_name),
                                             '\n'.join([strip_tags(paragraph.text) for paragraph in
                                                        driver.find_element_by_class_name('b-news-text ').find_elements_by_tag_name('p')]))

                    predicted_column = classify_text(content, [tfidf_w, tfidf_ch], class_model)

                    if predicted_column in columns:
                        print(f'Adding new article "{article_name}"')
                        news.append(f'{NUM_TO_ICONS[predicted_column]} [{strip_accents(article_name)}]({article_url})')

                except (StaleElementReferenceException, TimeoutException, Exception) as e:
                    print('#' * 50)
                    print(f'Exception appeared during parsing the {article_name} article: {e}')
                    print('skipping...')
                    print('#' * 50)

                print(f'sleeping another {sleep_time} seconds before the next article')
                time.sleep(sleep_time)

            if len(news) == batch:
                print(f'Returning {batch} news: {news}')
                bot.send_message(uid, '\n'.join(news), parse_mode='MarkdownV2', disable_web_page_preview=True)
                news = []

            known_user['last_article'] = news_ids[-1]

            if not known_user['online']:
                # Seems like /stop_search was requested. Closing the browser
                driver.quit()
                known_user['search_in_progress'] = False
                break

        else:
            print(f'Sleeping another hour (or so) before the next batch')
            time.sleep(random.randint(3600, 7200))
            continue

        print('Exiting as it seems /stop_search was called')
        return


if __name__ == "__main__":
    get_news()
