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

Docker image
------------

A Docker image is available on the `Docker Hub <https://hub.docker.com/r/nicolaslm/sauna/>`_. It
allows to run sauna in a container::

    $ docker pull nicolaslm/sauna

If you want to share the configuration between the host and the container using a volume, be
carreful about file permissions.

The configuration file might contains some sensible data like password and should not be readable
for everyone. But inside the container sauna runs as user *sauna* (uid 4343) and need to read the
configuration file. To do so, the easiest way is to create a user on the host with the same uid
(4343) and chown the configuration file with this user. Then you can mount the configuration file
inside the container and run sauna with ::

    $ docker run -v /etc/sauna.yml:/app/sauna.yml:ro nicolaslm/sauna
