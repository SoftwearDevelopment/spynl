=============================
Error Handling
=============================

Error Views
-----------
All HTML 400 errors go through the ``error400`` error view. All SpynlException errors will go through the ``spynl_error`` error view. All unexcected errors go trhough the ``error500`` view and will only get ``internal server error`` as a message.

SpynlException class
--------------------
An exception of the ``SpynlException`` (sub)class will go through the ``spynl_error`` exception endpoint. The response that is returned is defined in ``SpynlExcpetion`` and the error view makes sure that the exception is properly logged.

Messages
^^^^^^^^
There are several message types that can be set for a SpynlException in the ``__init__``.

The ``message`` is the message that is intended for the end user, it should be easy to read and not contain sensitive data.

The ``developer_message`` is intended for third party developers and while it can be technical, it should not contain any sensitive data.

The ``debug_message`` is meant for debugging, it will not be sent in the response, it will only be logged. It should be a normal string and never a translation string.

Extending the response
^^^^^^^^^^^^^^^^^^^^^^^^
If you want to expose more information than just the ``message`` and the ``developer_message`` you can extend the response in a subclass.

.. code:: python

    class CustomException(SpynlException):
    
        def make_response(self):
            response = super().make_response()
            response.update({'custom_info': 'This is a custom response'})
            return response



Mapping external Exceptions
---------------------------
You can map external exceptions to internal exceptions, so they raise a SpynlException with a proper error message, instead of resulting in an internal server error.

For this you need to import the external error and register it at an internal error:

.. code:: python

    from external_package import ExternalException

    @SpynlException.register_external_exception(ExternalException)
    class InternalException(SpynlException):
    
        def __init__(self):
            message = 'This is a Spynl message'
            super().__init__(message=message)
            self.extra = ''
	
        def set_external_exception(self, external_exception):
        """ This particular external exception has an entry called extra """
            super().set_external_exception(external_exception)
	    self.debug_message = str(self._external_exception)
	    self.extra = self._external_exception.extra

	def make_response(self):
        """ To add the extra information to the response, you need to extend it. """
            response = super().make_response()
            response.update({'extra': self.extra})
            return response


To be able to use this functionality, you will need to activate the ``view_deriver`` that handles catching the external errors and the mapping in one of your ``includeme()`` functions:

.. code:: python
	  
    from spynl.main.exceptions import catch_mapped_exceptions
    
        def includeme(config):
            # register the view deriver to catch mapped exceptions
            config.add_view_deriver(catch_mapped_exceptions)
