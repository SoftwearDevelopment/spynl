import os
from spynl.main.locale import SpynlTranslationString as _

def hello(request):
    """
    Say hello to the world.

    ---
    get:
      description: >
        This is a simple endpoint used for the basic Spynl tutorial.

        ####Response

        JSON keys | Content Type | Description\n
        --------- | ------------ | -----------\n
        status    | string | 'ok' or 'error'\n
        message   | string | Hello, world!\n

      tags:
        - my-package
      show-try: true
    """
    return dict(message=_('hello-msg', default="Hello, world!"))


def includeme(config):
    """
    Configure endpoints and translation path
    """
    config.add_endpoint(hello, 'hello')
    config.add_translation_dirs('%s/src/my-package/locale'
                                % os.environ['VIRTUAL_ENV'])
