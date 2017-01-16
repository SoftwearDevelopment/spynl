"""Custom (de)serialisation Exceptions"""


from spynl.main.exceptions import SpynlException
from spynl.main.locale import SpynlTranslationString as _


class UndeterminedContentTypeException(SpynlException):
    """Undetermined Content Type"""

    def __init__(self):
        """Exception message"""
        self.message =  _('undetermined-content-type-exception',
                          default='The request carries a body but the content type cannot be '
                          'determined.')


class UnsupportedContentTypeException(SpynlException):
    """Unsupported Content Type"""

    def __init__(self, content_type):
        """Exception message"""
        self.message =  _('unsupported-content-type-exception',
                          default='Unsupported content type: "${type}"',
                          mapping={'type': content_type})


class DeserializationUnsupportedException(SpynlException):
    """Deserialisation not supported"""

    def __init__(self, content_type):
        """Exception message"""
        self.message = _('deserialization-unsupported-exception',
                         default='Deserialization for content type "${type}" is '
                         'unsupported.',
                         mapping={'type': content_type})


class SerializationUnsupportedException(SpynlException):
    """Serialization not supported"""

    def __init__(self, content_type):
        """Exception message"""
        self.message = _('serialization-unsupported-exception',
                         default='Serialization for content type: "${type}" is '
                         'not supported.',
                         mapping={'type': content_type})
        return _('serialization-unsupported-exception',
                 default='Serialization for content type: "${type}" is '
                         'not supported.',
                 mapping={'type': self.args[0]})


class MalformedRequestException(SpynlException):
    """Malformed reqeust - first give content type, then message"""

    def __init__(self, content_type, request=None):
        """Exception message"""
        if request:
            self.message = _('malformed-request-exception-type',
                             default='Malformed "${type}" request: ${request}',
                             mapping={'type': content_type, 'request': request})
        else:
            self.message = _('malformed-request-exception',
                             default='Malformed request: ${type}',
                             mapping={'type': content_type})
