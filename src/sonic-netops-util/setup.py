#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages
from setuptools.command.build_py import build_py
from os import system, environ
from sys import exit

# read me
with open('README.rst') as readme_file:
    readme = readme_file.read()

setup(
    author="lnos-coders",
    author_email='lnos-coders@linkedin.com',
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="Package contains netops utilities Library sonic.",
    license="GNU General Public License v3",
    long_description=readme + '\n\n',
    include_package_data=True,
    keywords='sonic-netops-util',
    name='sonic-netops-util',
    py_modules=[],
    packages=[
        'netops_utils'
    ],
    install_requires=[
        'tabulate',
        'swsssdk'
    ],
    setup_requires= [
        'pytest-runner'
    ],
    tests_require = [
        'pytest'
    ],
    version='1.0',
    zip_safe=False,
)
