.. _cli:

Command Line Interface
======================

After a successful installation, the ``sauna`` command can be used to run and administer Sauna. An
explanation of the available commands and flags are given with ``sauna --help``::

    $ sauna --help
    Daemon that runs and reports health checks

    Usage:
      sauna [--level=<lvl>] [--config=FILE] [<command> <args>...]
      sauna sample
      sauna (-h | --help)
      sauna --version

    Options:
      -h --help      Show this screen.
      --version      Show version.
      --level=<lvl>  Log level [default: warn].
      --config=FILE  Config file [default: sauna.yml].

    Available commands:
      list-active-checks            Display the checks that sauna will run.
      list-available-checks         Display the available checks.
      list-available-consumers      Display the available consumers.
      status                        Show the result of active checks.

When no command is given, sauna runs in the foreground. It executes and sends the checks until
interrupted. Sauna can also run as a :ref:`service <service>` in the background.
