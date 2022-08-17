from setuptools import setup, find_packages
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
    license='BSD',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: System Administrators',
        'Topic :: System :: Monitoring',
        'Topic :: System :: Systems Administration',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],

    keywords='monitoring health checks nagios shinken',

    packages=find_packages(exclude=['tests']),

    install_requires=[
        'docopt',
        'PyYAML'
    ],

    extras_require={
        'tests': [
            'pytest',
            'pycodestyle',
            'requests-mock',
            'pymdstat',
            'jsonpath_rw',
            'psutil'
        ],
    },

    entry_points={
        'console_scripts': [
            'sauna = sauna.main:main',
        ],
    },

)
