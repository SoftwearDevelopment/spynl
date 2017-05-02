"""Custom (de)serialisation Exceptions."""


from spynl.main.exceptions import SpynlException
from spynl.main.locale import SpynlTranslationString as _


class UndeterminedContentTypeException(SpynlException):
    """Undetermined Content Type."""

    def __init__(self):
        """Exception message."""
        message = _('undetermined-content-type-exception',
                    default=('The request carries a body but the '
                             'content type cannot be determined.'))
        super().__init__(message=message)


class UnsupportedContentTypeException(SpynlException):
    """Unsupported Content Type."""

    def __init__(self, content_type):
        """Exception message."""
        message = _('unsupported-content-type-exception',
                    default='Unsupported content type: "${type}"',
                    mapping={'type': content_type})
        super().__init__(message=message)


class DeserializationUnsupportedException(SpynlException):
    """Deserialisation not supported."""

    def __init__(self, content_type):
        """Exception message."""
        message = _('deserialization-unsupported-exception',
                    default=('Deserialization for content type '
                             '"${type}" is unsupported.'),
                    mapping={'type': content_type})
        super().__init__(message=message)


class SerializationUnsupportedException(SpynlException):
    """Serialization not supported."""

    def __init__(self, content_type):
        """Exception message."""
        message = _('serialization-unsupported-exception',
                    default=('Serialization for content type: '
                             '"${type}" is not supported.'),
                    mapping={'type': content_type})
        super().__init__(message=message)


class MalformedRequestException(SpynlException):
    """Malformed reqeust - first give message then content type."""

    def __init__(self, content_type, error_cause=None):
        """Exception message."""
        if error_cause:
            message = _('malformed-request-exception-type',
                        default=('Malformed "${type}" request: '
                                 '${request}'),
                        mapping={'type': content_type,
                                 'request': error_cause})
        else:
            message = _('malformed-request-exception',
                        default='Malformed request: ${type}',
                        mapping={'type': content_type})
        super().__init__(message=message)
