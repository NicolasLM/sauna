#!/usr/bin/env python3
"""Daemon that runs and reports health checks

Documentation https://sauna.readthedocs.io

Usage:
  sauna [--level=<lvl>] [--config=FILE] [<command> <args>...]
  sauna sample
  sauna (-h | --help)
  sauna --version

Options:
  -h --help      Show this screen.
  --version      Show version.
  --level=<lvl>  Log level [default: warn].
  --config=FILE  Config file [default: sauna.yml].

Available commands:
"""
import sys
import logging
import logging.config

from docopt import docopt, DocoptLanguageError
from yaml.error import YAMLError

import sauna
from sauna import commands


def build_main_doc():
    sauna.Sauna.import_submodules('sauna.commands.ext')
    doc = __doc__
    for name, func in sorted(commands.CommandRegister.all_commands.items()):
        summary = func.__doc__ .splitlines()[0]
        doc += '  {:<28}  {}\n'.format(name, summary)
    return doc


def main():
    doc = build_main_doc()
    args = docopt(doc, version=sauna.__version__, options_first=True)
    conf_file = args['--config']
    logging.basicConfig(
        format='%(asctime)s - %(levelname)-8s - %(name)s: %(message)s',
        datefmt='%Y/%m/%d %H:%M:%S',
        level=getattr(logging, args['--level'].upper(), 'WARN')
    )

    # Sample command needs a not configured instance of sauna
    if args.get('<command>') == 'sample':
        sauna_instance = sauna.Sauna()
        file_path = sauna_instance.assemble_config_sample('./')
        print('Created file {}'.format(file_path))
        sys.exit(0)

    try:
        config = sauna.read_config(conf_file)
    except YAMLError as e:
        print('YAML syntax in configuration file {} is not valid: {}'.
              format(conf_file, e))
        sys.exit(1)

    if 'logging' in config:
        # Override the logging configuration with the one from the config file
        logging.config.dictConfig(config['logging'])

    sauna_instance = sauna.Sauna(config)

    # Generic commands implemented in sauna.commands package
    if args.get('<command>'):
        argv = [args['<command>']] + args['<args>']
        try:
            func = commands.CommandRegister.all_commands[args['<command>']]
        except KeyError:
            print('{} is not a valid command'.format(args['<command>']))
            sys.exit(1)
        try:
            command_args = docopt(func.__doc__, argv=argv)
        except DocoptLanguageError:
            command_args = None
        func(sauna_instance, command_args)

    # Just run sauna
    else:
        sauna_instance.launch()

    logging.shutdown()
