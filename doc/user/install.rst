.. _install:

Installation
============

Prerequisites
-------------

Sauna is written in Python 3, prior to use it you must make sure you have a Python 3 interpreter on
your system.

Pip
---

If you are familiar with the Python ecosystem, you won't be surprised that sauna can be installed
with::

    $ pip install sauna 

That's it, you can call it a day!

Debian package
--------------

A Debian package for Jessie is built with each release, you can find them on `GitHub
<https://github.com/NicolasLM/sauna/releases>`_.

Download and install the deb package::

    $ wget https://github.com/NicolasLM/sauna/releases/download/<version>/sauna_<version>-1_all.deb
    $ dkpg -i sauna_<version>-1_all.deb || apt-get install -f

The configuration file will be located at ``/etc/sauna.yml`` and sauna will be launched
automatically on boot.

Source Code
-----------

Sauna is developed on GitHub, you can find the code at `NicolasLM/sauna
<https://github.com/NicolasLM/sauna>`_.

You can clone the public repository::

    $ git clone https://github.com/NicolasLM/sauna.git

Once you have the sources, simply install it with::

    $ python setup.py install

If you are interested in writing your own checks, head up to the :ref:`development <custom>`.
