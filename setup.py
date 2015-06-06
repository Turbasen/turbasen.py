from distutils.core import setup

name = 'turbasen'
version = '1.0.0'

setup(
    name=name,
    packages=[name],
    version=version,
    description='Client for Nasjonal Turbase REST API',
    author='Ali Kaafarani',
    author_email='ali.kaafarani@turistforeningen.no',
    url='https://github.com/Turbasen/turbasen.py',
    download_url='https://github.com/Turbasen/turbasen.py/tarball/v%s' % (version),
    keywords=['turbasen', 'nasjonalturbase', 'turistforening', 'rest-api'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: Norwegian',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],
    install_requires=['requests'],
)
