"""Helper functions for translation task."""


import os

from spynl.main.pkg_utils import get_dev_config


def languages_from_dev_config():
    """Return languages from dev configparser."""
    languages = get_dev_config().get('spynl.languages')
    if isinstance(languages, str):
        languages = [lang for lang in languages.split(',') if lang != '']
    return languages


def get_or_create_locale_path():
    """
    Return the locale path.

    If locale path is not found, create one in the current working directory
    and return that one.
    """
    for path, dirs, _ in os.walk(os.path.abspath(os.getcwd())):
        if 'locale' in dirs:
            locale_path = path
            print("[spynl dev.translate] Located locale folder in"
                  " %s ..." % locale_path)
            break
    else:  # make locale folder if it doesn't exist already
        print("[spynl dev.translate] Creating locale folder ...")
        os.mkdir('locale')
        locale_path = '.'
    return locale_path
