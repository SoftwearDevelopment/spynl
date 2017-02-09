=======================================
Spynl - write a web app you can manage 
=======================================

Spynl is a Python web framework which extends the  `Pyramid <http://getpyramid.com>`_ web framework.

**Spynl helps you to manage your web application:**

* **Build** your app (via `Jenkins <https://jenkins.io>`_)
* **Deploy** your app (via `Docker <https://www.docker.com/what-docker>`_)
* Serve **endpoint documentation** for frontend devs (via `Swagger <http://swagger.io/>`_)
* **Inspect** settings and meta-data of running instances in the browser
* **Aggregate** performance indicators and error messages in `NewRelic <https://newrelic.com>`_ and/or `Sentry <https://sentry.io>`_

Spynl also has a few other in-built utilities which are often necessary in a modern professional web application but easily take a few days to get right:

* Manage translations (via `Babel <http://babel.pocoo.org>`_)
* Send templatable, translatable HTML emails
* validate JSON input and output with Schemas


Installation
---------------------

Here is a (very) quick How-To for installing Spynl:

.. code:: bash

    $ pip install spynl
    $ spynl dev.serve

Now you can visit Spynl's in-built /about endpoint:

.. code:: bash

    $ curl http://localhost:6543/about

And you should get a reponse like this:

.. code:: json

    {
        "status": "ok",
        "language": "en",
        "time": "2017-02-03T10:13:41+0000",
        "plugins": {},
        "message": "This is a Spynl web application. You can get more information at about/endpoints, about/ini, about/versions, about/build and about/environment.",
        "spynl_version": "6.0.1"
    }

So you see there are a few endpoints with more specific information. Try visiting http://localhost:6543/about/endpoints to see the documentation for in-built endpoints and http://localhost:6543/about/ini to see possible settings.

The *plugins* part is empty because we haven't written any code of our own yet.
See the next section for that.


Short developer tutorial
--------------------------

A small tutorial where we build up a small app step by step.

.. toctree::
   :maxdepth: 2

   developer-tutorial


Short operations tutorial
---------------------------

We show what steps are necessary to get your Spynl-based app built, deployed and
smoke-tested.

.. toctree::
   :maxdepth: 2

   building-deploying-tutorial


In-depth documentation
--------------------------

Shining more light on a few important topics (work in progress):

.. toctree::
    :maxdepth: 2
    :glob:

    in-depth/*

