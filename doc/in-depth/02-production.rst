===============================
Your production environment(s)
===============================

You'll probably have a dev environment and at least one production(-like) environment.
Spynl helps you to:

* keep the code consistent between deploys to each of them
* Make sure test do not affect real users and unfinished things are turned off
  in production
* allow a third party to control your prodcution pipeline


Docker
---------------

We use Docker to ship Spynl. You can be sure there that you look at the same
code in dev and production. (`/about/versions` can help you to look up
precisely which code is in there).

`/about/build` helps you to see when the Image was made (built on Jenkins) and when it was started.

The image is Ubuntu-based. 

Custom pre-install and post-install hooks are possible in `setup.sh` (also works for `dev.install`)
    
`prepare-docker-run.sh` can influence `production.ini` or other relevant things
in the Docker container right before it is run.


Possibilities to turn off endpoints and whole resources on production
-----------------------------------------------------------------------

(TODO: add issue about a more generic approach)


Do not send emails to real addresses from non-production environments
----------------------------------------------------------------------

TODO: link to the email section


Using different container registries for dev and for production 
-----------------------------------------------------------------

Useful if you keeo them separated or a thrid party manages your production
pipeline (e.g. when using a DTAP approach).

