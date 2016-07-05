#!/usr/bin/env python3
"""Daemon that runs and reports health checks

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
import logging

from docopt import docopt, DocoptLanguageError

import sauna
from sauna import commands


def build_main_doc():
    sauna.Sauna.import_submodules('sauna.commands.ext')
    doc = __doc__
    for name, func in sorted(commands.CommandRegister.all_commands.items()):
        summary = func.__doc__ .splitlines()[0]
        doc += '  {}  - {}\n'.format(name, summary)
    return doc


def main():
    doc = build_main_doc()
    args = docopt(doc, version=sauna.__version__, options_first=True)
    conf_file = args['--config']
    logging.basicConfig(
        format='%(asctime)s - %(levelname)-8s - %(message)s',
        datefmt='%Y/%m/%d %H:%M:%S',
        level=getattr(logging, args['--level'].upper(), 'WARN')
    )
    logging.getLogger('requests').setLevel(logging.ERROR)

    if args.get('<command>') == 'sample':
        # Sample command needs a not configured instance of sauna
        sauna_instance = sauna.Sauna()
        file_path = sauna_instance.assemble_config_sample('./')
        print('Created file {}'.format(file_path))
    elif args.get('<command>'):
        # Generic commands implemented in sauna.commands package
        config = sauna.read_config(conf_file)
        sauna_instance = sauna.Sauna(config)
        argv = [args['<command>']] + args['<args>']
        try:
            func = commands.CommandRegister.all_commands[args['<command>']]
        except KeyError:
            print('{} is not a valid command'.format(args['<command>']))
            exit(1)
        try:
            command_args = docopt(func.__doc__, argv=argv)
        except DocoptLanguageError:
            command_args = None
        func(sauna_instance, command_args)
    else:
        # Just run sauna
        config = sauna.read_config(conf_file)
        sauna_instance = sauna.Sauna(config)
        sauna_instance.launch()

    logging.shutdown()
