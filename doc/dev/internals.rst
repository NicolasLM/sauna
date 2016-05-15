.. _internals:

Internals
=========

This page provides the basic information needed to start hacking sauna. It presents how it works
inside and how the project is designed.

Design choices
--------------

Easy to install
~~~~~~~~~~~~~~~

Installing software written in Python can be confusing for some users. Getting a Python interpreter
is not an issue but installing the code and its dependencies is.

The Python ecosystem is great, so many high quality libraries are available for almost anything.
While it is okay for a web application to require dozens of dependencies, it is not for a simple
monitoring daemon that should run on any Unix box.

Most of the times checks are really basics, they involve reading files, contacting APIs... Often
these things can be done in one line of code using a dedicated library, or 10 using the standard
library. The latter has the advantage of simplifying the life of the end user.

Of course it does not mean that sauna has to do everything from scratch, sometimes it's fine to get
a little help. For instance the `psutil <https://github.com/giampaolo/psutil>`_ library is so
convenient for retrieving system metrics that it would be foolish not to rely on it. On the other
hand getting statistics from memcached is just a matter of opening a socket, sending a few bytes
and reading the result. It probably does not justify adding an extra dependency that someone may
have a hard time installing.

Batteries included, but removable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sauna tries its best to provide a set of core plugins that are useful to system administrators. But
for instance, a user not interested in monitoring system metrics should be able to opt-out of
system plugins. This reduces the footprint of sauna and doesn't require to user to install external
dependencies that he will never use.

Python 3 only
~~~~~~~~~~~~~

Not supporting Python 2 simplifies the code base.

Python 3 has been around for about 8 years, it is available on every distribution and starts to
replace Python 2 as the default interpreter on some of them. Most of the libraries in the Python
ecosystem are compatible with the version 3.

Efficient
~~~~~~~~~

Sauna tries to consume as little resources as possible. Your server probably has more important
things to do than checking itself.

Very often monitoring tools rely on launching external processes to fetch metrics from other
systems. How often have you seen a program firing a ``/bin/df -h`` and parsing the output to
retrieve the disk usage?

This puts pressure on the system which has to fork processes, allocate memory and handle context
switches, while most of the times its possible to use a dedicated API to retrieve the information,
in this case the ``/proc`` file system.

Concurrency
-----------

Main thread
~~~~~~~~~~~

The main thread is responsible for setting up the application, launching the workers, handling
signals and tearing down the application. It creates one producer thread and some consumer threads. 

Producer
~~~~~~~~
The producer is really simple, it is a loop that creates instances of plugins, run the checks and
goes to sleep until it needs to loop again. Check results are appended to the consumers' queues.

Consumers
~~~~~~~~~

Consumers exits in two flavors: with and without a queue. Queued consumers are synchronous, when
they receive a check in their queue they use it straight away. The :py:class:`NSCAConsumer`, for
instance, gets a check and sends it to a monitoring server.

Asynchronous consumers do not have a queue, instead when they need to know the status of a check,
they read it in a shared dictionary containing the last instance of all checks. A good example is
the :py:class:`TCPServerConsumer`, it waits until a client connects to read the statuses from the
dictionary.

Each consumer runs on its own thread to prevent one consumer from blocking another.

Thread safety
~~~~~~~~~~~~~

Queues are instances of :py:class:`queue.Queue` which handles the locking behind the scenes.

Asynchronous consumers must only access the ``check_results`` shared dictionary after acquiring a
lock::

    with check_results_lock:
        # do somethin with check_results

