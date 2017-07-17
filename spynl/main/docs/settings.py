"""
Set-up for ini documentation list of dicts

In the ini_doc list, only use 'yes' or 'no' for the required field,
as this is used in the code to check if all required settings are set.
"""

from spynl.main.exceptions import SpynlException


ini_description = '''
These are the settings that can be added to the ini file under the heading
[app:main]. This table only lists settings specific to Spynl. Pyramid settings
and Pyramid Mail configuration should also be put in [app:main], but are not
listed here.  Spynl will not start if one of the required settings is not
present in the ini file. <br>
The pyramid asbool function returns the boolean value True if the case-lowered
value of string input s is any of t, true, y, on, or 1, otherwise return the
boolean value False. If s is the value None, return False. If s is already one
of the boolean values True or False, return it. <br>
N.B. It is not possible to add comments after the setting,
comments should be on their own line.
'''

ini_doc = [{'name': 'spynl.date_systemtz',
            'plugin': '',
            'required': 'no',
            'default': 'UTC',
            'info': 'Timezone that is used if no time zone is explicitly '
                    'given and also no time zone is found in or to be '
                    'used from the user object.'},

           {'name': 'spynl.date_format',
            'plugin': '',
            'required': 'no',
            'default': '%Y-%m-%dT%H:%M:%S%z',
            'info': 'Format for dates.'},

           {'name': 'spynl.languages',
            'plugin': '',
            'required': 'no',
            'default': 'en',
            'info': 'A csv string describing the languages supported by the '
                    'application (other than english). Spynl has no dialect '
                    'support, so only two-letter language codes should be '
                    'provided. The first language is considered to be the '
                    'preferred language. This setting can affect which '
                    'langauge Spynl picks for a request and also how the task '
                    '<spynl dev.translate> works.'},

           {'name': 'spynl.domain',
            'plugin': '',
            'required': 'no',
            'default': 'localhost',
            'info': 'Used for setting the cookie-domain, and for a default '
                    'no-reply emailaddress.'},

           {'name': 'spynl.tld_origin_whitelist',
            'plugin': '',
            'required': 'no',
            'default': '',
            'info': 'Comma-separated whitelist for allowed origins. '
                    'It is expected to hold only the top-level domains, '
                    ' e.g. "google.com".'},

           {'name': 'spynl.dev_origin_whitelist',
            'plugin': '',
            'required': 'no',
            'default': '',
            'info': 'Comma separated whitelist for allowed origins which is '
                    'usable for a development context. It is expected to hold'
                    ' either complete domains or mere protocols, e.g. '
                    '"chrome-extension://"..'},

           {'name': 'spynl.pretty',
            'plugin': '',
            'required': 'no',
            'default': 'false',
            'info': 'Pretty printing for development. Is read with Pyramid '
                    'asbool function.'},

           {'name': 'spynl.session',
            'plugin': '',
            'required': 'no',
            'default': 'Pyramid',
            'info': 'Sets the name of the session class to use. Spynl will '
                    'look this class up under settings[<name>]. '
                    'The class should conform to the interface '
                    'pyramid.interfaces.ISession. The value "Pyramid" or '
                    'omitting this setting will result in the use of the '
                    'Session class from beaker.session'},

           {'name': 'spynl.ops.environment',
            'plugin': '',
            'required': 'no',
            'default': '',
            'info': 'The environment Spynl is running in. This is quite '
                    'useful for things like error log aggregation.'},

           {'name': 'spynl.ops.function',
            'plugin': '',
            'required': 'no',
            'default': '',
            'info': 'The function this Spynl node is performing. This '
                    'can be useful for error log aggregation if you '
                    ' employ more than one Spynl applications.'},

           {'name': 'spynl.ops.jenkins_url',
            'plugin': '',
            'required': 'no',
            'default': '',
            'info': 'The URL of your Jenkins server.'},

           {'name': 'spynl.ops.dev_url',
            'plugin': '',
            'required': 'no',
            'default': '',
            'info': 'The URL where your development app can be '
                    'accessed. Needed to run smoke tests after deploys.'},

           {'name': 'spynl.ops.dev_domain',
            'plugin': '',
            'required': 'no',
            'default': '',
            'info': 'The top level domain on which your development app '
                    'resides. This is used to get the cookie domain '
                    'correct.'},

           {'name': 'spynl.ops.ecr.dev_tasks',
            'plugin': '',
            'required': 'no',
            'default': 'dev',
            'info': 'The tasks supported in your development AWS ECR.'},

           {'name': 'spynl.ops.ecr.dev_url',
            'plugin': '',
            'required': 'no',
            'default': '',
            'info': 'The URL of your AWS ECR used for development. Include '
                    'AWS profile name like this: profile@ecr-url.'},

           {'name': 'spynl.ops.ecr.prod_url',
            'plugin': '',
            'required': 'no',
            'default': '',
            'info': 'The URL of your AWS ECR used for production. Include '
                    'AWS profile name like this: profile@ecr-url.'},

           {'name': 'spynl.sentry.key',
            'plugin': '',
            'required': 'no',
            'default': '',
            'info': 'The key used to connect to Sentry. Leave empty if '
                    'you are not using Sentry.'},

           {'name': 'spynl.sentry.project',
            'plugin': '',
            'required': 'no',
            'default': '',
            'info': 'The project identifier Spynl reports to in Sentry.'},

           {'name': 'spynl.newrelic.key',
            'plugin': '',
            'required': 'no',
            'default': '',
            'info': 'The key used to connect to NewRelic. Leave empty if '
                    'you are not usig NewRelic.'}
          ]


def get_ini_doc_setting(name):
    """
    Returns the documentation entry of a specific setting or None

    Because ini_doc is a list, this function is needed to get the documentation
    of a specific setting.
    """
    for setting in ini_doc:
        if setting['name'] == name:
            return setting

    return None


def check_required_settings(config):
    """check whether all required ini settings are set"""
    for setting in ini_doc:
        if (setting['required'] == 'yes' and
                setting['name'] not in config.registry.settings):
            msg = 'Please set {} in the Pyramid ini file'.format(
                setting['name'])
            raise SpynlException(msg)
        # setting['required'] can only be yes or no (no accidental true's)
        if setting['required'] not in ('no', 'yes'):
            msg = ('The value for required in ini_doc can only be yes or no, '
                   'please change this for setting: {}'
                   .format(setting['name']))
            raise SpynlException(msg)
