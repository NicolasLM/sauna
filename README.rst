Sauna
=====

Sauna is a small daemon designed to run health checks and send the results to a
monitoring server. It is able to report to Nagios and Shinken out of the box.

It is made to be resource efficient (it avoids forking at all costs), simple
to install and low maintenance.

Installation
------------

A Debian package compatible with wheezy and jessie is available. Grab the
`latest release <https://github.com/NicolasLM/sauna/releases>`_ on Github
and install it::

   dkpg -i sauna_<version>_all.deb || apt-get install -f

Alternatively, Sauna is available on PyPI, you can install it with pip::

   pip install sauna

Usage
-----

Start by generating a sample configuration file ``sauna-sample.yml``::

   sauna sample

Edit the sample configuration to fit your system, pick the plugins that you
want and choose a consumer. When you are done move the file as ``sauna.yml``.

Start sauna::

   sauna

You can easily run it as a daemon using systemd or supervisor. Startup
scripts are included in the Debian package.

Using Sauna you will manipulate two entities: plugins and consumers.

Plugins
~~~~~~~

Plugins are optional modules that provide a set of checks. You only opt-in
for the plugins that make sense for your setup. Available plugins are:

* Load average
* Memory and swap usage
* Disk partition usage
* Processes and file descriptors
* Redis
* External command
* Puppet agent
* Postfix
* Memcached

Consumers
~~~~~~~~~

Consumers on the other hand provide a way for checks to be processed by a
central monitoring server.

Sauna can be both passive and active at the same time. From the monitoring
server point of view, active consumers are the one where the monitoring
server requests a status update and passive when the monitoring receive status
updates.

Available consumers are:

* NSCA (passive)
* HTTP (passive)
* TCP server (active)
* Stdout (passive)

Contributing
------------

Sauna is written in Python 3. Adding a check plugin or a consumer should be
straightforward. Clone the repository and install it in development mode in a
virtualenv::

   pip install -e .

The code base follows pep8, test the code for compliance with::

   pep8 sauna tests

Run the test suite::

   nosetests

License
-------

MIT
