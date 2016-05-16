.. Sauna documentation master file, created by
   sphinx-quickstart on Fri May  6 22:17:12 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Sauna
=====

Release v\ |version|. (:ref:`Installation <install>`)

Sauna is a lightweight daemon designed to run health checks and send the results to a monitoring
server.

Sauna comes batteries included, it is able run many system checks (load, memory, disk...) as well
as monitor applications (redis, memcached, puppet...). It is easily :ref:`extensible <custom>` to
include your own checks and can even run the thousands of existing :ref:`Nagios plugins <nagios>`.

Painless monitoring of your servers is just a pip install away::

    pip install sauna

Getting started with sauna:

.. toctree::
   :maxdepth: 1

   user/install
   user/configuration
   user/service
   user/plugins
   user/consumers
   user/cookbook
   user/faq

Development guide:

.. toctree::
   :maxdepth: 1

   dev/custom
   dev/contributing
   dev/internals
