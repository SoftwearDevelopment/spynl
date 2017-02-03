==========================
ini-settings
==========================

/about/ini
-----------

Spynl checks required settings on startup
-----------------------------------------

Documenting your own settings
---------------------------------

.. code:: python

    from spynl.main.docs.settings import ini_doc
    my_ini_doc = ...
    ini_doc.extend(my_ini_doc)
