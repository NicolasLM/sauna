.. _service:

Launching on boot
=================

You will probably want to launch sauna as a service as opposed as attached to a shell. This page
presents a few possibilities for doing that.

.. note:: If you installed sauna via the Debian package, everything is already taken care of and
          you can skip this part.

Creating a user
---------------

Sauna does not need to run as root, following the principle of least privilege, you should create a
user dedicated to sauna::

    adduser --system --quiet --group --no-create-home sauna

Systemd
-------

If your distribution comes with the systemd init system, launching sauna on boot is simple.
Create a :download:`systemd unit file <../../debian/sauna.service>` at
``/etc/systemd/system/sauna.service``::

    [Unit]
    Description=Sauna health check daemon
    Wants=network-online.target
    After=network-online.target

    [Service]
    Type=simple
    ExecStart=/opt/sauna/bin/sauna --config /etc/sauna.yml
    User=sauna

    [Install]
    WantedBy=multi-user.target

Indicate in ``ExecStart`` the location where you installed sauna and in ``User`` which user will
run sauna.

Enable the unit, as root::

   # systemctl daemon-reload 
   # systemctl enable sauna.service
   Created symlink to /etc/systemd/system/sauna.service.
   # systemctl start sauna.service
   # systemctl status sauna.service
   ● sauna.service - Sauna health check daemon
      Loaded: loaded (/etc/systemd/system/sauna.service; enabled)
      Active: active (running) since Sat 2016-05-14 13:13:16 CEST; 1min 17s ago
    Main PID: 30613 (sauna)
      CGroup: /system.slice/sauna.service
              └─30613 /opt/sauna/bin/python3.4 /opt/sauna/bin/sauna --config /etc/sauna.yml 

Supervisor
----------

`Supervisor <http://supervisord.org/index.html>`_ is a lightweight process control system used in
addition of init systems like systemd or SysVinit.

Create a supervisor definition for sauna::

    [program:sauna]
    command=/opt/sauna/bin/sauna --config /etc/sauna.yml
    user=sauna 

Load the new configuration::

    $ supervisorctl reread
    $ supervisorctl update
