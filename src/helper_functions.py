from itertools import chain
import os
import pickle
import string

from src.settings import PROJ_PATH


def load_object(path, func):
    """
    Loads the serialized object from the provided path using func serializer.
    """

    file_path = os.path.join(PROJ_PATH, 'src', path)

    if func == pickle:
        if not os.path.exists(file_path):
            return None

        with open(file_path, 'rb') as f:
            return func.load(f)

    else:
        if not os.path.exists(file_path):
            return {}

        with open(file_path, encoding='utf-8') as f:
            return func.load(f)


def save_object(obj, path, func):
    """
    Serializes the obj object using func serializer and dumps it into the file by the provided path.
    """

    file_path = os.path.join(PROJ_PATH, 'src', path)

    if func == pickle:
        with open(file_path, 'wb') as f:
            func.dump(obj, f)

    else:
        with open(file_path, 'w', encoding='utf-8') as f:
            func.dump(obj, f)


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
