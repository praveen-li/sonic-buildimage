#!/usr/bin/env python

from setuptools import setup

setup(
   name='sonic-platform',
   version='1.0',
   description='SONiC platform API implementation on Cisco platforms',
   license='Apache 2.0',
   author='SONiC Team',
   author_email='abhiaga2@cisco.com',
   url='https://github.com/Azure/sonic-buildimage',
   maintainer='Abhishek Agarwal',
   maintainer_email='abhiaga2@cisco.com',
   packages=[
      'sonic_platform',
   ],
   install_requires=[
       'sonic-platform-common',
       'sonic-py-common'
   ],
   classifiers=[
       'Development Status :: 3 - Alpha',
       'Environment :: Plugins',
       'Intended Audience :: Developers',
       'Intended Audience :: Information Technology',
       'Intended Audience :: System Administrators',
       'License :: OSI Approved :: Apache Software License',
       'Natural Language :: English',
       'Operating System :: POSIX :: Linux',
       'Programming Language :: Python :: 3.7',
       'Topic :: Utilities',
    ],
   keywords='sonic SONiC platform PLATFORM',
)
