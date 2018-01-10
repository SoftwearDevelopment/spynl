"""Validate and load request's keys/values before accessing the view."""


from functools import wraps
from inspect import getfullargspec

from marshmallow import Schema

from ..exceptions import BadQueryString


class QueryStringSchema(Schema):
    """Handle in one place schema loading errors for schemas that inherit from this."""

    def handle_error(self, exc, data):
        raise BadQueryString(developer_message=dict(message='Invalid query string.',
                                                    errors=exc.messages))


def query_string_loader(schema):
    """Validate query string key/values and load the data before accessing the view function."""
    def wrapper(view):
        """Return the decorator."""
        @wraps(view)
        def load(*args, **kwargs):
            """Update request.args with the loaded ones and execute the view function."""
            request = args[-1]  # request is always the last argument
            data, _ = schema.load(request.GET)
            request.args.update(data)

            if len(getfullargspec(view).args) == 1:
                return view(request)
            else:
                return view(*args)
        return load
    return wrapper
