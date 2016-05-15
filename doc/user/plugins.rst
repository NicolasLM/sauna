.. _plugins:

Plugins
=======

Plugins contains checks that sauna can run to determine the health of the system. Sauna will
periodically run the checks contained in active plugins and forward the results to active
:ref:`consumers <consumers>`.

Plugins can either be core ones shipped with sauna, or :ref:`your own plugins <custom>` for
monitoring the specific parts of your system.

.. todo:: Find a way to automatically document core plugins. For now you can find the list of core
          `plugins on GitHub <https://github.com/NicolasLM/sauna/tree/master/sauna/plugins/ext>`_.
