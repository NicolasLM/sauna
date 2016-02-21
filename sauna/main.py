#!/usr/bin/env python3
"""Health checker

Usage:
  health.py sample [PATH]
  health.py [PATH] [--level=<lvl>]
  health.py (-h | --help)
  health.py --version

Options:
  -h --help      Show this screen.
  --version      Show version.
  --level=<lvl>  Log level [default: info].

"""
import logging

from docopt import docopt

import sauna


def main():
    args = docopt(__doc__, version=sauna.__version__)
    path = args['PATH'] or ''
    logging.basicConfig(
        format='%(asctime)s - %(levelname)-8s - %(message)s',
        datefmt='%Y/%m/%d %H:%M:%S',
        level=getattr(logging, args['--level'].upper(), 'INFO')
    )
    logging.getLogger('requests').setLevel(logging.ERROR)

    if args.get('sample'):
        file_path = sauna.assemble_config_sample(path)
        print('Created file {}'.format(file_path))

    else:
        sauna.launch(path)

    logging.shutdown()
