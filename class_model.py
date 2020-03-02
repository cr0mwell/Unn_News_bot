import json
import os
import pickle

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from stop_words import get_stop_words
from pymorphy2 import MorphAnalyzer
from scipy.sparse import hstack

from settings import COLS_TO_NUM


# Apply TfidfVectorizers to the texts and build the dataset
def get_dataset(texts, vects, fit=False):
    """
    Fits/transforms the texts(list) using the provided vectorizers(list)
    and returns the scipy.sparse matrix based on the obtained features.
    """

    data = None

    for vect in vects:
        if fit:
            vect.fit(texts)
        if data is not None:
            data = hstack((data, vect.transform(texts)))
        else:
            data = vect.transform(texts)

    return data


def get_w_vectorizer():
    with open(os.path.join('src', 'class_tfidf_w.vct'), 'rb') as f:
        return pickle.load(f)


def get_ch_vectorizer():
    with open(os.path.join('src', 'class_tfidf_ch.vct'), 'rb') as f:
        return pickle.load(f)


def get_model():
    with open(os.path.join('src', 'class_model_log.md'), 'rb') as f:
        return pickle.load(f)


def create_model():
    """
    Main function that generates LogisticRegression model and saves it to 'src/clas_model_log.md'.
    It also creates TF-IDF vectorizers and saves them to 'src/class_tfidf_w.vct', 'src/class_tfidf_ch.vct'
    """

    # Reading the news from the file
    try:
        with open(os.path.join('src', 'categorized_news.json'), encoding='utf-8') as f:
            print('Parsing file for news')
            content = json.load(f)
            article_names = []
            texts = []
            headings = []

            for id in content.keys():
                from spider import strip_accents  # avoiding circular imports

                article_names.append(strip_accents(content[id]['name']))
                texts.append(strip_accents(content[id]['text']))
                headings.append(content[id]['category'])
    except FileNotFoundError:
        print("Can't find 'categorized_news.json'. Please generate it using 'spider.py'")
        raise

    ######################
    # Feature engineering
    ######################
    morph = MorphAnalyzer(lang='uk')

    def stemmed_text(text):
        return ' '.join([morph.parse(tok)[0].normal_form for tok in text.split(' ')])

    STOP_WORDS = stemmed_text(' '.join(get_stop_words('ukrainian'))).split(' ')
    CLASSES    = list(COLS_TO_NUM.keys())

    # Encoding the target label
    le = LabelEncoder()
    le.fit(CLASSES)
    headings = le.transform(headings)
    print('Encoded target classes')

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

    # Splitting the texts into train/test folds
    texts_train, texts_test, y_train, y_test = train_test_split([[text] for text in texts],
                                                                headings,
                                                                test_size=0.2,
                                                                stratify=headings,
                                                                random_state=42)

    # As texts_train, texts_test are now list of lists ([['foo'], ['bar']]), converting them to lists (['foo', 'bar'])
    texts_train = [t[0] for t in texts_train]
    texts_test = [t[0] for t in texts_test]

    # Apply TfidfVectorizers to the texts and build the combined train/test matrices
    tfidf_w.fit(texts_train)
    tfidf_ch.fit(texts_train)

    # Collecting feature names
    tfidf_w_labels = [k for k, v in sorted(list(tfidf_w.vocabulary_.items()), key=lambda x: x[1])]
    tfidf_ch_labels = [k for k, v in sorted(list(tfidf_ch.vocabulary_.items()), key=lambda x: x[1])]

    w_train = tfidf_w.transform(texts_train)
    ch_train = tfidf_ch.transform(texts_train)
    train_ds = hstack([w_train, ch_train])

    w_test = tfidf_w.transform(texts_test)
    ch_test = tfidf_ch.transform(texts_test)
    test_ds = hstack([w_test, ch_test])
    print('Collected the dataset')

    # Saving the dataset
    # save_npz(os.path.join(PROJ_PATH, 'src', 'class_data.npz'), all_ds)

    # Saving the vectorizer objects
    print('Saving vectorizers')
    with open(os.path.join('src', 'class_tfidf_w.vct'), 'wb') as f:
        pickle.dump(tfidf_w, f)

    with open(os.path.join('src', 'class_tfidf_ch.vct'), 'wb') as f:
        pickle.dump(tfidf_ch, f)

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
    with open(os.path.join('src', 'class_model_log.md'), 'wb') as f:
        pickle.dump(log_reg, f)

    print('All operations complete successfully')


if __name__ == "__main__":
    create_model()
