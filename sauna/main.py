#!/usr/bin/env python3
"""Health checker

Usage:
  sauna [--level=<lvl>] [--config=FILE]
  sauna sample
  sauna list-active-checks [--config=FILE]
  sauna list-available-checks [--config=FILE]
  sauna list-available-consumers [--config=FILE]
  sauna (-h | --help)
  sauna --version

Options:
  -h --help      Show this screen.
  --version      Show version.
  --level=<lvl>  Log level [default: warn].
  --config=FILE  Config file [default: sauna.yml].

"""
import logging

from docopt import docopt

import sauna


def main():
    args = docopt(__doc__, version=sauna.__version__)
    conf_file = args['--config']
    logging.basicConfig(
        format='%(asctime)s - %(levelname)-8s - %(message)s',
        datefmt='%Y/%m/%d %H:%M:%S',
        level=getattr(logging, args['--level'].upper(), 'WARN')
    )
    logging.getLogger('requests').setLevel(logging.ERROR)

    if args.get('sample'):
        sauna_instance = sauna.Sauna()
        file_path = sauna_instance.assemble_config_sample('./')
        print('Created file {}'.format(file_path))
    else:
        config = sauna.read_config(conf_file)
        sauna_instance = sauna.Sauna(config)
        if args.get('list-active-checks'):
            for name in sauna_instance.get_active_checks_name():
                print('{}'.format(name))
        elif args.get('list-available-checks'):
            for plugin, checks in\
                    sauna_instance.get_all_available_checks().items():
                print('{}: {}'.format(plugin, ', '.join(checks)))
        elif args.get('list-available-consumers'):
            for consumer in sauna_instance.get_all_available_consumers():
                print('{}'.format(consumer))
        else:
            sauna_instance.launch()

    logging.shutdown()
