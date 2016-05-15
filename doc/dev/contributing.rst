.. _contributing:

Contributing
============

This page contains the few guidelines and conventions used in the code base.

Pull requests
-------------

The development of sauna happens on GitHub, the main repository is
`https://github.com/NicolasLM/sauna <https://github.com/NicolasLM/sauna>`_. To contribute to sauna:

* Fork ``NicolasLM/sauna``
* Clone your fork
* Create a feature branch ``git checkout -b my_feature``
* Commit your changes
* Push your changes to your fork ``git push origin my_feature``
* Create a GitHub pull request against ``NicolasLM/sauna``'s master branch

.. note:: Avoid including multiple commits in your pull request, unless it adds value to a future
          reader. If you need to modify a commit, ``git commit --amend`` is your friend. Write a
          meaningful commit message, see `How to write a commit message
          <http://chris.beams.io/posts/git-commit/>`_.

Python sources
--------------

The code base follows `pep8 <https://www.python.org/dev/peps/pep-0008/>`_ guidelines with lines
wrapping at the 79th character. You can verify that the code follows the conventions with::

    $ pep8 sauna tests

Running tests is an invaluable help when adding a new feature or when refactoring. Try to add the
proper test cases in ``tests/`` together with your patch. The test suite can be run with nose::

    $ nosetests
    ....................................
    ----------------------------------------------------
    Ran 36 tests in 0.050s

    OK

Compatibility
-------------

Sauna runs on all versions of Python 3 starting from 3.2. Tests are run on Travis to ensure that.
Except from a few import statements, this is usually not an issue.

Documentation sources
---------------------

Documentation is located in the ``doc`` directory of the repository. It is written in
`reStructuredText <http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html>`_ and built
with `Sphinx <http://www.sphinx-doc.org/en/stable/index.html>`_.

For ``.rst`` files, the line length is 99 chars as opposed of the 79 chars of python sources.

If you modify the docs, make sure it builds without errors::

    $ cd doc/
    $ make html

The generated HTML pages should land in ``doc/_build/html``.
