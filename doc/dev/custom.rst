.. _custom:

Writing custom checks
=====================

Sauna ships with its own plugins for standard system monitoring, but sometimes you need more. This
guide is a quick tutorial to start writing your own Python plugins to extend sauna's checks.

If writing Python is not an option, binaries written is any language can be run through the
:ref:`Command plugin <nagios>`.

For the sake of learning we will create the Uptime plugin. It will contain a simple check that will
alert you when the uptime for your machine is under a threshold. This could be used to get a
notification when a server rebooted unexpectedly.

Custom plugins directory
------------------------

Your custom plugins must live somewhere on your file system. Let's say ``/tmp/sauna_plugins``::

    $ mkdir /tmp/sauna_plugins

This directory will contain `Python modules <https://docs.python.org/3/tutorial/modules.html>`_,
like our ``uptime.py``::

    $ cd /tmp/sauna_plugins
    $ touch uptime.py

The Uptime class
----------------

All plugins have in common the same Python class ``Plugin``, so the quite not working simplest
implementation of a plugin is::

    from sauna.plugins import Plugin

    class Uptime(Plugin):
        pass

This implementation must be registered into sauna to be used to launch checks, as often in Python,
this is done through a bit of decorator magic::

    from sauna.plugins import Plugin, PluginRegister

    my_plugin = PluginRegister('Uptime')

    @my_plugin.plugin()
    class Uptime(Plugin):
        pass

Here we are, a minimal class that is a sauna plugin. Now let's create our check.

The uptime check
----------------

A check is simply a method of the Plugin that is marked as a check, again through a decorator::


    @my_plugin.plugin()
    class Uptime(Plugin):

        @my_plugin.check()
        def uptime(self, check_config):
            return self.STATUS_OK, 'Uptime looks good'

So far we have an ``Uptime`` plugin, with an ``uptime`` check that always returns a positive
status. Here is a bit of convention about checks: they must return a tuple containing the status
(okay, warning, critical or unknown) and a human readable string explaining the result.

Arguably this check is not really useful, let's change that by actually fetching the uptime from
``/proc/uptime``::

    @my_plugin.check()
    def uptime(self, check_config):
        with open('/proc/uptime') as f:
            uptime_seconds = float(f.read().split()[0])
        return (self._value_to_status_more(uptime_seconds, check_config),
                'Uptime is {}'.format(timedelta(seconds=uptime_seconds)))

The ``check_config`` passed to your check method contains the information needed to run the
check and generate a status, it contains for instance the warning and critical thresholds. The
value of uptime in seconds can be compared to the threshold with ``_value_to_status_more``, which
returns the correct status.

If during the execution of the check an exception is thrown, for instance if the ``/proc`` file
system is not available, the check result will have the status ``unknown``.

The final plugin
----------------

All these snippets together give the final plugin code::

    from datetime import timedelta

    from sauna.plugins import Plugin, PluginRegister

    my_plugin = PluginRegister('Uptime')

    @my_plugin.plugin()
    class Uptime(Plugin):

        @my_plugin.check()
        def uptime(self, check_config):
            with open('/proc/uptime') as f:
                uptime_seconds = float(f.read().split()[0])
            return (self._value_to_status_more(uptime_seconds, check_config),
                    'Uptime is {}'.format(timedelta(seconds=uptime_seconds)))

Configuring sauna to use Uptime
-------------------------------

In the last step of this tutorial you need to tell sauna where to find your plugin, this is done
through the ``extra_plugins`` configuration parameter. It is a list of directories where sauna will
look for modules:

.. code-block:: yaml

    ---
    periodicity: 10
    extra_plugins:
      - /tmp/sauna_plugins

    consumers:

      Stdout:
 
    plugins:

      - type: Uptime
        checks:
          - type: uptime
            warn: 300
            crit: 60

You can verify that sauna found your plugin by listing the available checks::

    $ sauna list-available-checks

    Load: load1, load15, load5
    Uptime: uptime
    [...]

Finally run sauna::

    $ sauna

    ServiceCheck(name='uptime_uptime', status=0, output='Uptime is 4 days, 1:24:19.790000')
