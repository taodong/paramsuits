#!/usr/bin/env python
import setuptools

name = 'paramsuits'
version = '0.0.1'

with open('README.md', 'r') as fh:
    long_description = fh.read()
 
setuptools.setup(
    name = name,
    version = version,
    author = 'Tao Dong',
    author_email = 'taojdcn@gmail.com',
    description = 'A tool to manage parameters in AWS SSM parameter store',
    long_description = long_description,
    long_description_content_type = 'text/markdown',
    packagesv= setuptools.find_packages(),              
    scripts = ['paramsuits.py'],
    license = 'Apache2',
    url = 'https://github.com/taodong/paramsuits',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators'
    ],
    install_requires = [
        'boto3 >= 1.4.6'
    ],
    entry_points = {
        'console_scripts': [
            'paramsuits = paramsuits:main'
        ]
    }
)