"""Sets up Spynl."""


import os
import sys
import codecs
import re
from setuptools import setup, find_packages


here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()


install_requires = ['webob==1.6.3', 'pyramid>=1.7,<1.8', 'invoke>=0.14,<0.15', 'requests',
                    'pyramid_mailer', 'pyramid_jinja2', 'pyramid_exclog',
                    'pytz', 'pbkdf2', 'python-dateutil', 'html2text',
                    'beaker', 'waitress', 'gunicorn', 'jsonschema',
                    'sphinx', 'pyyaml', 'tld', 'babel',
                    'webtest', 'pytest', 'pytest-raisesregexp']


def find_version(*file_paths):
    """ get the version string from a file path."""
    version_file = codecs.open(os.path.join(here, *file_paths), 'r').read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


def pytest_runner_dependency():
    """Return a list that contains the pytest_runner dependency if needed"""
    needs_pytest = {'pytest', 'test', 'ptr'}.intersection(sys.argv)
    return ['pytest-runner'] if needs_pytest else []


setup(name='spynl',
      version=find_version('spynl', 'main', 'version.py'),
      description='spynl',
      long_description=README,
      classifiers=["Programming Language :: Python3"
                   "Framework :: Pylons",
                   "Topic :: Internet :: WWW/HTTP",
                   "Topic :: Internet :: WWW/HTTP :: WSGI :: Application"],
      author='Softwear BV',
      author_email='development@softwear.nl',
      url='http://www.softwear.nl',
      keywords='API SaaS',
      packages=find_packages(), # spynl, spynl.main.*, spynl.test
      include_package_data=True,
      zip_safe=False,
      install_requires=install_requires,
      setup_requires=pytest_runner_dependency() + ['PasteScript'],
      test_suite="spynl",
      entry_points={
          "paste.app_factory": ["main = spynl.main:main"],
          "console_scripts": ["spynl = cli.spynlcli:program.run"]
      },
      paster_plugins=['pyramid']
)
