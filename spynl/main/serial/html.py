"""If needed, Spynl can return an HTML response."""

from spynl.main.serial.xml import prettify_xml


DOCTYPE = '<!DOCTYPE html>'


def dumps(content, pretty=False):
    """format an HTML response"""
    # only prettify HTML if necessary
    if pretty and "<html><" in content and "<body><" in content:
        tags = ['<' + e for e in content.split('<') if e != ""]
        content = ''.join(prettify_xml(tags))
    if not content.lstrip().startswith("<!DOCTYPE"):
        content = DOCTYPE + content
    return '{}{}'.format(pretty * '\n', content)
