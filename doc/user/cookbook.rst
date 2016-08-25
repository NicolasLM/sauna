.. _cookbook:

Cookbook
========

This page provides recipes to get the best out of sauna.

HAProxy health checks
---------------------

When load balancing servers with HAProxy you might want to enable health checks. If one of your
servers is running out of memory, overloaded or not behaving properly you can remove it from the
pool of healthy servers.

To help you achieve that sauna has a special consumer that listens on a TCP port and returns the
status of the server when getting an incoming connection. This consumer is the ``TCPServer``
consumer.

Enabling the TCP server
~~~~~~~~~~~~~~~~~~~~~~~

To enable the TCP server add it to the list of :ref:`active consumers <configuration_consumers>`::

    ---
    consumers:

      TCPServer:
        port: 5555

Let's launch sauna and try to connect to the port 5555::

    $ nc localhost 5555
    OK

As the system is healthy sauna answers ``OK``. Let's try by switching a check to ``CRITICAL``::

    $ nc localhost 5555
    CRITICAL

Configuring HAProxy
~~~~~~~~~~~~~~~~~~~

We will configure HAProxy to remove a server from the pool as soon as it is not in ``OK`` state.
For that we will use `tcp-check
<https://www.haproxy.com/doc/aloha/7.0/haproxy/healthchecks.html#checking-any-service>`_.

Assuming you have a load balancing frontend/backend already set up, activate checks::

    backend webfarm
        mode http
        option tcp-check
        tcp-check connect port 5555
        tcp-check expect string OK
        server web01 10.0.0.1:80 check
        server web02 10.0.0.2:80 check
        server web03 10.0.0.3:80 check

* ``option tcp-check`` enables level 3 health checks
* ``tcp-check connect port 5555`` tells HAProxy to check the port 5555 of servers in the pool
* ``tcp-check expect string OK`` consider the server down if it does not answer ``OK``

.. _nagios:

Reusing Nagios plugins
----------------------

Nagios plugins are still very popular, their simple API can be considered the de facto standard for
monitoring checks. Sauna can run Nagios plugins through its ``Command`` plugin.

Here we will run the famous ``check_http`` for monitoring Google. Add a ``Command`` plugin to
:ref:`sauna.yml <configuration_plugins>`::

    ---
    plugins:

      - type: Command
        checks:
          - type: command
            name: check_google
            command: /usr/lib/nagios/plugins/check_http -H www.google.com

Run sauna::

    $ sauna
    ServiceCheck(name='check_google', status=0, output='HTTP OK: HTTP/1.1 302 Found')

.. note:: Nagios plugins may be convenient but they rely on forking a process for each check.
          Consider using some of the lighter sauna core plugins if this is an issue.

Passive host checks
-------------------

When it is not possible to check if a host is alive by sending a ping (for instance when the host
is in a private network), Nagios and Shinken can use passive host checks submitted via NSCA.

Passive host checks work like normal service checks, except that they don't carry a service name::

    ---
    plugins:

      - type: Dummy
        checks:
          - type: dummy
            name: ""
            status: 0
            output: Host is up and running

Configure your monitoring server to consider your host down if no passive host check has been
received for one minute::

    define host {
        address                192.168.20.3
        host_name              test
        use                    generic-host
        check_command          check_dummy!2
        active_checks_enabled  0
        passive_checks_enabled 1
        check_freshness        1
        freshness_threshold    60
    }
