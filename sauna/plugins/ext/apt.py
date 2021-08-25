from sauna.plugins import Plugin, PluginRegister

my_plugin = PluginRegister('Apt')


@my_plugin.plugin()
class AptPlugin(Plugin):

    def __init__(self, config):
        super().__init__(config)
        try:
            import apt
            self._apt = apt
        except ImportError:
            from ... import DependencyError
            raise DependencyError(
                self.__class__.__name__,
                'apt',
                deb='python3-apt'
            )
        self._packages = None

    @property
    def packages(self) -> list:
        if self._packages is None:
            with self._apt.Cache() as cache:
                cache.upgrade()  # Only reads the packages to upgrade
                self._packages = cache.get_changes()
        return self._packages

    @my_plugin.check()
    def security_updates(self, check_config):
        num_security_packages = 0
        for p in self.packages:
            for o in p.candidate.origins:
                if 'security' in o.codename.lower():
                    num_security_packages += 1
                    break

                if 'security' in o.label.lower():
                    num_security_packages += 1
                    break

                if 'security' in o.site.lower():
                    num_security_packages += 1
                    break

        if num_security_packages == 0:
            return self.STATUS_OK, 'No security updates'

        return (
            self.STATUS_WARN,
            f'{num_security_packages} packages with security updates'
        )

    @my_plugin.check()
    def package_updates(self, check_config):
        if not self.packages:
            return self.STATUS_OK, 'No package updates'

        return (
            self.STATUS_WARN,
            f'{len(self.packages)} packages updates'
        )

    @staticmethod
    def config_sample():
        return '''
        # Debian APT
        # This only consults the local APT cache, it does not
        # run an 'apt update'. Use 'unattended-upgrades' for that.
        - type: Apt
          checks:
            - type: security_updates
            - type: package_updates
        '''
