from sauna.commands import CommandRegister

list_commands = CommandRegister()


@list_commands.command(name='list-active-checks')
def list_active_checks(sauna_instance, args):
    """Display the checks that sauna will run."""
    for name in sorted(sauna_instance.get_active_checks_name()):
        print(name)


@list_commands.command(name='list-available-checks')
def list_available_checks(sauna_instance, args):
    """Display the available checks."""
    for plugin, checks in sorted(
            sauna_instance.get_all_available_checks().items()
    ):
        print('{}: {}'.format(plugin, ', '.join(checks)))


@list_commands.command(name='list-available-consumers')
def list_available_consumers(sauna_instance, args):
    """Display the available consumers."""
    for c in sorted(sauna_instance.get_all_available_consumers()):
        print(c)
