"""Generic custom exceptions for all packages to use."""

from pyramid.httpexceptions import HTTPBadRequest, HTTPForbidden

from spynl.main.locale import SpynlTranslationString as _


class SpynlException(Exception):
    """
    The Superclass for all Spynl-specific Exceptions.

    If your Exception inherits from this, the Spynl Error handling
    can treat it differently, e.g. show its message.
    You can also specify with which HTTP exception it should be
    escalated.

    param message: A message for the enduser. Exposed, should NOT contain
                   sensitive data.
    param developer_message: A message for 3rd party users of our API.
                             Exposed, should NOT contain sensitive data.
    param debug_message: A message for internal use when debugging.
    """
    http_escalate_as = HTTPBadRequest

    def __init__(self,
                 message='an internal error has occured',
                 developer_message=None,
                 debug_message=None):
        self.message = message
        self.developer_message = developer_message or self.message
        self.debug_message = debug_message or self.message

    def make_response(self):
        """
        Return a response as a dictionary.

        If an exception needs to store additional information in the reponse
        it can be overriden in the following way.

        >>> def make_reponse(self):
                data = super().make_response()
                data.update({
                    'extra': 'Some extra information'
                })
                return data
        """
        response = {
            'status': 'error',
            'type': self.__class__.__name__,
            'message': self.message,
            'developer_message': getattr(self,
                                         'developer_message',
                                         self.message)
        }

        return response

    def __str__(self):
        """This will return a str version of the message. If the message is a
        SpynlTranslationString, it will return an interpolated version of the
        default (no translation).
        """
        return str(self.message)


class BadOrigin(SpynlException):
    """Bad origin exception."""

    http_escalate_as = HTTPForbidden

    def __init__(self, origin):
        """Set the origin attribute."""
        self.origin = origin
        self.message = _(u'bad-origin',
                         default="Requests to the Spynl API are not "
                         "permitted from origin '${origin}'.",
                         mapping={'origin': self.origin})


class IllegalAction(SpynlException):
    """Raise if the desired action is not allowed."""

    def __init__(self, message):
        """Exception message."""
        self.message = message


class MissingParameter(SpynlException):
    """Exception when parameter is missing."""

    def __init__(self, param):
        """Exception message."""
        self.message = _('missing-parameter',
                         default='Missing required parameter: ${param}',
                         mapping={'param': param})


class IllegalParameter(SpynlException):
    """Exception when parameter is illegal."""

    def __init__(self, param):
        """Exception message."""
        self.message = _('illegal-parameter',
                         default='Illegal parameter: ${param}',
                         mapping={'param': param})


class BadValidationInstructions(SpynlException):
    """Exception when the validation documentation cannot be used."""

    def __init__(self, error):
        """Exception message."""
        self.message = _('bad-validation-instructions',
                         default='The description of validations for this'
                         ' endpoint cannot be used: ${error}',
                         mapping={'error': error})


class InvalidResponse(SpynlException):
    """Exception when the response should be validated, but could not."""

    def __init__(self, error):
        """Exception message."""
        self.message = _('invalid-response',
                         default='Spynl could not generate a valid response: ${error}',
                         mapping={'error': error})


class EmailTemplateNotFound(SpynlException):
    """Exception when email template file is not found."""

    def __init__(self, template):
        """Exception message."""
        self.message = _('email-tmpl-not-found',
                         default='The email template <${template}> was not found.',
                         mapping={'template': template})


class EmailRecipientNotGiven(SpynlException):
    """Exception when there is no recipient for the email """

    def __init__(self):
        """Exception message."""
        self.message = _('email-recipient-not-given',
                         default='You did not give a recipient for the email.')
