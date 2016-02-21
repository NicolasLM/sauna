"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""
from setuptools import setup
from codecs import open
from os import path

from sauna import __version__ as version

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='sauna',
    version=version,
    description='Daemon that runs and reports health checks',
    long_description=long_description,
    url='https://github.com/NicolasLM/sauna',
    author='Nicolas Le Manchet',
    author_email='nicolas@lemanchet.fr',
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: System Administrators',
        'Topic :: System :: Monitoring',
        'Topic :: System :: Systems Administration',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],

    keywords='monitoring health checks nagios shinken',

    packages=['sauna'],

    install_requires=[
        'docopt',
        'PyYAML'
    ],

    entry_points={
        'console_scripts': [
            'sauna=sauna.main:main',
        ],
    },

)
