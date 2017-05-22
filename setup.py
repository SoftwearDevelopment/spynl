"""Sets up Spynl."""

import codecs
import os
import re

from setuptools import setup, find_packages


here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()


install_requires = [
    'webob==1.6.3',
    'pyramid>=1.7,<1.8',
    'requests',
    'pyramid_mailer',
    'pyramid_jinja2',
    'pyramid_exclog',
    'pytz',
    'pbkdf2',
    'python-dateutil',
    'html2text',
    'beaker',
    'waitress',
    'jsonschema',
    'pyyaml',
    'tld',
    'click',
    'babel',
]

extras_require = {
    'tests': ['pytest', 'pytest-raisesregexp', 'pytest-runner', 'webtest'],
    'docs': ['sphinx'],
    'server': ['gunicorn'],
}


def find_version(*file_paths):
    """ get the version string from a file path."""
    version_file = codecs.open(os.path.join(here, *file_paths), 'r').read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    name='spynl',
    version=find_version('spynl', 'main', 'version.py'),
    description='spynl',
    long_description=README,
    classifiers=["Programming Language :: Python :: 3.5",
                 "Framework :: Pylons",
                 "Topic :: Internet :: WWW/HTTP",
                 "Topic :: Internet :: WWW/HTTP :: WSGI :: Application"],
    author='Softwear BV',
    author_email='development@softwear.nl',
    url='https://github.com/SoftwearDevelopment/spynl',
    license='MIT',
    keywords='API SaaS',
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    extras_require=extras_require,
    test_suite="spynl",
    entry_points={
        "paste.app_factory": ["main = spynl.main:main"],
        "console_scripts": ["spynl = spynl.cli.commands:cli"]
    },
    paster_plugins=['pyramid']
)
