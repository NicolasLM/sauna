from sauna.commands import CommandRegister

status_commands = CommandRegister()


@status_commands.command(name='status')
def list_active_checks(sauna_instance, args):
    """Show the result of active checks."""
    human_status = {
        0: 'OK',
        1: 'Warning',
        2: 'Critical',
        3: 'Unknown',
    }
    for check in sorted(sauna_instance.launch_all_checks()):
        print('  {:<30} {:^14} {}'.format(
            check.name, human_status[check.status], check.output
        ))
