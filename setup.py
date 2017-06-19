from setuptools import setup

name = 'turbasen'
VERSION = '3.2.0'

setup(
    name=name,
    packages=[name],
    version=VERSION,
    description='Client for Nasjonal Turbase REST API',
    long_description='Documentation: https://turbasenpy.readthedocs.io/',
    author='Ali Kaafarani',
    author_email='tekno@dnt.no',
    url='https://github.com/Turbasen/turbasen.py',
    download_url='https://github.com/Turbasen/turbasen.py/tarball/v%s' % (VERSION),
    keywords=['turbasen', 'nasjonalturbase', 'turistforening', 'rest-api'],
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: Norwegian',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
    ],
    install_requires=['requests>=2.10.0,<3'],
    extras_require={
        'dev': ['sphinx', 'ipython', 'flake8'],
    }
)
