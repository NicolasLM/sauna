Sauna
=====

Sauna is a lightweight daemon designed to run health checks and send the results to a monitoring
server.

Sauna comes batteries included, it is able run many system checks (load, memory, disk...) as well
as monitor applications (redis, memcached, puppet...). It is easily extensible to include your own
checks and can even run the thousands of existing Nagios plugins.

Installation
------------

You can install it with pip::

   pip install sauna

See the `documentation <https://sauna.readthedocs.io/en/latest/user/install.html>`_ for other
installation methods.

Documentation
-------------

Documentation for sauna is available at `sauna.readthedocs.io
<https://sauna.readthedocs.io/en/latest/>`_.

Plugins
~~~~~~~

Plugins are optional modules that provide a set of checks. You only opt-in for the plugins that
make sense for your setup. Available plugins are:

* Load average
* Memory and swap usage
* Disk partition usage
* Processes and file descriptors
* Redis
* External command
* Puppet agent
* Postfix
* Memcached
* HTTP servers

Consumers
~~~~~~~~~

Consumers on the other hand provide a way for checks to be processed by a monitoring server.
Available consumers are:

* NSCA
* HTTP
* TCP server
* Stdout

Contributing
------------

Sauna is written in Python 3. Adding a check plugin or a consumer should be straightforward. Clone
the repository and install it in development mode in a virtualenv::

   pip install -e .

The code base follows pep8, test the code for compliance with::

   pep8 sauna tests

Run the test suite::

   nosetests

More information about how to contribute are available on the `development guide
<https://sauna.readthedocs.io/en/latest/dev/contributing.html>`_.

License
-------

BSD
