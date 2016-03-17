import subprocess
import shlex

from sauna.plugins import Plugin, PluginRegister

myplugin = PluginRegister('Command')


@myplugin.plugin()
class Command(Plugin):

    @myplugin.check()
    def command(self, check_config):
        p = subprocess.Popen(
            shlex.split(check_config['command']),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        stdout, _ = p.communicate()
        return p.returncode, stdout

    @staticmethod
    def _return_code_to_status(cls, return_code):
        if return_code in (cls.STATUS_OK, cls.STATUS_WARN, cls.STATUS_CRIT):
            return return_code
        return cls.STATUS_UNKNOWN

    @staticmethod
    def config_sample():
        return '''
        # Execute external command
        # Return code is the service status
        Command:
          checks:
            - type: command
              name: check_website
              command: /opt/check_website.sh
        '''
