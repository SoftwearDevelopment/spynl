======================
Custom get_user_info
======================

A lot of code needs information about the current (authenticated) user, e.g. in endpoints or for logging.

The in-built get_user_info function
-------------------------------------

Writing your own
-------------------

.. code:: python

    def my_user_info(request, purpose=None)
        pass # TODO
    
    config.add_settings(user_info_function=my_user_info)


