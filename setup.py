from setuptools import setup

from io import open
from os import path

name = 'turbasen'
VERSION = '2.1.3'

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name=name,
    packages=[name],
    version=VERSION,
    description='Client for Nasjonal Turbase REST API',
    long_description=long_description,
    author='Ali Kaafarani',
    author_email='ali.kaafarani@turistforeningen.no',
    url='https://github.com/Turbasen/turbasen.py',
    download_url='https://github.com/Turbasen/turbasen.py/tarball/v%s' % (VERSION),
    keywords=['turbasen', 'nasjonalturbase', 'turistforening', 'rest-api'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: Norwegian',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],
    install_requires=['requests'],
)
