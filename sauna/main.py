#!/usr/bin/env python3
"""Health checker

Usage:
  main.py sample
  main.py [--level=<lvl>] [--config=FILE]
  main.py (-h | --help)
  main.py --version

Options:
  -h --help      Show this screen.
  --version      Show version.
  --level=<lvl>  Log level [default: info].
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
        level=getattr(logging, args['--level'].upper(), 'INFO')
    )
    logging.getLogger('requests').setLevel(logging.ERROR)

    if args.get('sample'):
        file_path = sauna.assemble_config_sample('./')
        print('Created file {}'.format(file_path))

    else:
        sauna.launch(conf_file)

    logging.shutdown()
