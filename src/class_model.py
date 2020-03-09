import json
import os
import pickle

from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from stop_words import get_stop_words
from pymorphy2 import MorphAnalyzer

from src.helper_functions import (load_object, save_object, strip_accents)
from src.settings import (PROJ_PATH, COLS_TO_NUM)

CLASS_MODEL = None  # classification model object
VECTORIZERS = None  # list of vectorizer objects
CLASSES     = list(COLS_TO_NUM.keys())


def load_news():
    """
    Loads the news from the 'categorized_news.json' file.
    Splits the data into train/test sets using sklearn.model_selection.train_test_split.
    Returns a tuple of lists (X_train, X_test, y_train, y_test)
    """

    print("Parsing 'categorized_news.json' file for news")

    news_file = os.path.join(PROJ_PATH, 'src', 'categorized_news.json')
    if not os.path.exists(news_file):
        raise FileNotFoundError(f"'{news_file}' file was not found. Please run spider.py to get news for the dataset.")

    content  = load_object('categorized_news.json', json)
    texts    = []
    headings = []

    for id in content.keys():
        texts.append(strip_accents(content[id]['text']))
        headings.append(content[id]['category'])

    # Encoding the target label
    print('Encoding target classes')
    le = LabelEncoder()
    le.fit(CLASSES)
    headings = le.transform(headings)

    # Splitting the texts into train/test folds
    texts_train, texts_test, y_train, y_test = train_test_split([[text] for text in texts],
                                                                headings,
                                                                test_size=0.2,
                                                                stratify=headings,
                                                                random_state=42)

    # As texts_train, texts_test are now list of lists ([['foo'], ['bar']]), converting them to lists (['foo', 'bar'])
    texts_train = [t[0] for t in texts_train]
    texts_test  = [t[0] for t in texts_test]

    return texts_train, texts_test, y_train, y_test


def create_vectorizers():
    """
    Loads the news from 'categorized_news.json' and creates two vectorizer objects
    with 'word' and 'char' analyzers. Saves them to 'class_tfidf_w.vct' and 'class_tfidf_ch.vct' files respectively.
    """

    print('Creating vectorizer objects')
    texts_train, _, _, _ = load_news()

    morph = MorphAnalyzer(lang='uk')

    def stemmed_text(text):
        return ' '.join([morph.parse(tok)[0].normal_form for tok in text.split(' ')])

    STOP_WORDS = stemmed_text(' '.join(get_stop_words('ukrainian'))).split(' ')

    # word vectorizer object
    tfidf_w = TfidfVectorizer(analyzer='word',  # token = word
                              sublinear_tf=True,
                              ngram_range=(1, 2),  # (1, 1) - only unigrams are used, (1,2) - unigrams/bigrams, etc.
                              stop_words=STOP_WORDS,  # list of words to filter or None
                              vocabulary=None,  # or dict - own_dictionary of words to process
                              max_df=0.8,  # a frequency limit to filter the words by
                              max_features=5000,  # only top N words will be used as columns,
                              smooth_idf=True,
                              norm='l2'  # euclidean norm is used by default
                              )

    # char vectorizer object
    tfidf_ch = TfidfVectorizer(analyzer='char',  # token = word
                               ngram_range=(2, 6),  # (1, 1) - only unigrams are used, (1,2) - unigrams/bigrams, etc.
                               vocabulary=None,  # or dict - own_dictionary of words to process
                               max_df=0.8,  # a frequency limit to filter the words by
                               max_features=15000,  # only top N words will be used as columns,
                               smooth_idf=True,
                               norm='l2'  # euclidean norm is used by default
                               )

    # Apply TfidfVectorizers to the texts and build the combined train/test matrices
    tfidf_w.fit(texts_train)
    tfidf_ch.fit(texts_train)

    # Saving the vectorizer objects
    print('Saving vectorizers')
    save_object(tfidf_w, 'class_tfidf_w.vct', pickle)
    save_object(tfidf_ch, 'class_tfidf_ch.vct', pickle)


def get_vectorizers():
    """
    If VECTORIZERS is not set
    loads vectorizers objects from the 'class_tfidf_w.vct' and 'class_tfidf_ch.vct' files.
    Returns vectorizers objects as list.
    """

    global VECTORIZERS

    if VECTORIZERS is None:
        if not all(map(os.path.exists, [os.path.join(PROJ_PATH, 'src', 'class_tfidf_w.vct'),
                                        os.path.join(PROJ_PATH, 'src', 'class_tfidf_ch.vct')])):
            create_vectorizers()

        VECTORIZERS = [load_object('class_tfidf_w.vct', pickle),
                       load_object('class_tfidf_ch.vct', pickle)]

    return VECTORIZERS


def get_dataset(texts, vectorizers, fit=False):
    """
    Fits/transforms the texts(list) using the provided vectorizers(list)
    and returns the scipy.sparse matrix based on the obtained features.
    """

    data = None

    for vect in vectorizers:
        if fit:
            vect.fit(texts)
        if data is not None:
            data = hstack((data, vect.transform(texts)))
        else:
            data = vect.transform(texts)

    return data


def create_class_model():
    """
    Main function that generates LogisticRegression model and saves it to 'src/clas_model_log.md'.
    """

    print('Creating LogisticRegression model for news classification. This operation may take a while...')

    ######################
    # Feature engineering
    ######################

    texts_train, texts_test, y_train, y_test = load_news()
    tfidf_w, tfidf_ch = get_vectorizers()

    print('Collecting the dataset')
    w_train = tfidf_w.transform(texts_train)
    ch_train = tfidf_ch.transform(texts_train)
    train_ds = hstack([w_train, ch_train])

    w_test = tfidf_w.transform(texts_test)
    ch_test = tfidf_ch.transform(texts_test)
    test_ds = hstack([w_test, ch_test])

    # Saving the dataset
    # save_npz(os.path.join(PROJ_PATH, 'src', 'class_data.npz'), all_ds)

    ###########################
    # LogisticRegression model
    ###########################

    # Training the model
    print('Training LogisticRegression model')
    classifier = LogisticRegression(solver='saga')
    log_reg = classifier.fit(train_ds, y_train)

    # Predicting
    print('Predicting test target with LogisticRegression model')
    log_predictions = log_reg.predict(test_ds)

    # Evaluating with f1 weighted score (words & chars)
    print(f'Test evaluation: {f1_score(y_test, log_predictions, average="weighted")}')
    print(f'Train evaluation: {f1_score(y_train, log_reg.predict(train_ds), average="weighted")}')

    print(classification_report(y_test, log_predictions, zero_division=True, target_names=CLASSES))

    # Saving the model. sklearn models are not JSON serializable unfortunately
    print('Saving the LogisticRegression model')
    save_object(log_reg, 'class_model_log.md', pickle)

    print('All operations complete successfully')


def get_class_model():
    """
    Returns CLASS_MODEL value if it's set.
    Loads the classification model from the './class_model_log.md' file.
    If the file doesn't exist creates a new model and saves it to the file.
    """

    global CLASS_MODEL

    if CLASS_MODEL is None:
        if not os.path.exists(os.path.join(PROJ_PATH, 'src', 'class_model_log.md')):
            create_class_model()

        CLASS_MODEL = load_object('class_model_log.md', pickle)

    return CLASS_MODEL


if __name__ == "__main__":
    create_class_model()