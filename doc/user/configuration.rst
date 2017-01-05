.. _configuration:

Configuration
=============

Location
--------

Sauna configuration is made of a single yaml file. By default it loads ``sauna.yml`` in the current
directory. You can load another configuration file with the ``--config`` switch::

    $ sauna --config /etc/sauna.yml

.. note:: This configuration file might end up containing secrets to access your monitoring server.
          It is a good idea not to make it world readable. Only the user running sauna needs to
          be able to read it.

Quickstart
----------

Sometimes simply editing a configuration file feels easier than reading documentation. You can
generate a default configuration file::

    $ sauna sample
    Created file ./sauna-sample.yml

You can adapt this default configuration to fit your needs, when you are ready rename it and launch
sauna::

   $ mv sauna-sample.yml sauna.yml

Content
-------

The configuration yaml file contains three parts:

* Generic parameters
* Active consumers
* Active plugins

Generic parameters
~~~~~~~~~~~~~~~~~~

All these parameters can be left out, in this case they take their default value.

**periodicity**
    How often, in seconds, will checks be run. The default value of 120 means that sauna will run
    all checks every two minutes.
    Individual checks that need to run more or less often can override their ``periodicity``
    parameter.

**hostname**
    The name of the host that will be reported to monitoring servers. The default value is the
    fully qualified domain name of your host.

**extra_plugins**
    A list of directories where :ref:`additional plugins <custom>` can be found. Defaults to no
    extra directory, meaning it does not load plugins beyond the core ones.

**include**
    A path containing other configuration files to include. It can be used to separate each plugin
    in its own configuration file. File globs are expanded, example ``/etc/sauna.d/*.yml``.

**concurrency**
    How many threads can process the checks at the same time. The default value of 1 means sauna will
    run checks one by one.
    Note that activating the concurrency system will, by default, only allow 1 check with the same name to run at the
    same time.

Example::

    ---
    periodicity: 10
    extra_plugins:
      - /opt/sauna_plugins

.. _configuration_consumers:

Active consumers
~~~~~~~~~~~~~~~~

A list of the consumers you want to process your checks. It defines how sauna will interact with
your monitoring server(s).

Example::
   
    ---
    consumers:

      - type: NSCA
        server: receiver.shinken.tld
        port: 5667
        timeout: 10

Many consumers can be active at the same time and a consumer may be used more than once.

.. _configuration_plugins:

Active plugins
~~~~~~~~~~~~~~

A list of plugins and associated checks. 

Example::

    ---
    plugins:

    # Usage of disks
    - type: Disk
      checks:
        - type: used_percent
          warn: 80%
          crit: 90%
        - type: used_inodes_percent
          warn: 80%
          crit: 90%
          periodicity: 300
 
A plugin may be defined many times in the list. This allows to run the same checks with different
configurations parameters.

Plugin parameters
'''''''''''''''''

Some plugins accept additional configuration options, for example::

    - type: Redis
      checks: ...
      config:
        host: localhost
        port: 6379

Unfortunately the parameters accepted by each plugins are not yet documented.

Check parameters
''''''''''''''''

**type**
    The kind of check as defined by the plugin. All types available are listed by the command
    ``sauna list-available-checks``.

**warn**
    The warning threshold for the check.

**crit**
    The critical threshold for the check.

**name**
    Optional, overrides the default generated name of the check which is in the form
    ``plugin_type``. It becomes necessary to override the name when more than one checks of the
    same plugin and type are defined simultaneously.

**periodicity**
    Optional, overrides the global periodicity for this check. Used to run a check at a different
    frequency than the others.
