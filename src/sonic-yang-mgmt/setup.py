#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages
from setuptools.command.build_py import build_py
from os import system
from sys import exit


# important reuirements parameters
build_requirements = ['../../target/debs/stretch/libyang0.16_0.16.105-1_amd64.deb',
                      '../../target/debs/stretch/libyang-cpp0.16_0.16.105-1_amd64.deb',
                      '../../target/debs/stretch/python2-yang_0.16.105-1_amd64.deb']

install_requirements = []

setup_requirements = ['pytest-runner',]

test_requirements = ['pytest>=3', ]

# read me
with open('README.rst') as readme_file:
    readme = readme_file.read()

# class for prerequisites to build this package
class pkgBuild(build_py):
    """Custom Build PLY"""

    def run (self):
        # json file for YANG model test cases.
        test_yangJson_file = './tests/yang-model-tests/yangTest.json'
        # YANG models are in below dir
        yang_model_dir = './yang-models/'
        # yang model tester python module
        yang_test_py = './tests/yang-model-tests/yangModelTesting.py'
        #  install libyang
        for req in build_requirements:
            if 'target/debs'in req:
                pkg_install_cmd = "sudo dpkg -i {}".format(req)
                if (system(pkg_install_cmd)):
                    print("{} installed".format(req))
                else:
                    print("{} installtion failed".format(req))

        #  run tests for yang models
        test_yang_cmd = "python {} -f {} -y {}".format(yang_test_py, test_yangJson_file, yang_model_dir)
        if (system(test_yang_cmd)):
            print("YANG Tests failed\n")
            # below line will be uncommented after libyang python support PR #
            exit(1)
        else:
            print("YANG Tests passed\n")

        # Continue usual build steps
        build_py.run(self)


setup(
    cmdclass={
        'build_py': pkgBuild,
    },
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
    description="Package contains YANG models for sonic.",
    install_requires=install_requirements,
    license="GNU General Public License v3",
    long_description=readme + '\n\n',
    include_package_data=True,
    keywords='sonic_yang_mgmt',
    name='sonic_yang_mgmt',
    packages=find_packages(),
    setup_requires=setup_requirements,
    version='1.0',
    data_files=[
        ('yang-models', ['./yang-models/sonic-head.yang',
                         './yang-models/sonic-acl.yang',
                         './yang-models/sonic-interface.yang',
                         './yang-models/sonic-port.yang',
                         './yang-models/sonic-portchannel.yang',
                         './yang-models/sonic-vlan.yang']),
    ],
    zip_safe=False,
)
