from setuptools import setup

name = 'turbasen'
VERSION = '2.3.6'

setup(
    name=name,
    packages=[name],
    version=VERSION,
    description='Client for Nasjonal Turbase REST API',
    long_description='See https://github.com/Turbasen/turbasen.py/blob/master/README.md',
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
