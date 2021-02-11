from setuptools import setup

dependencies = [
    'redis==2.10.6',
    'psutil'
]

high_performance_deps = [
    'hiredis>=0.1.4'
]

setup(
    name='sonic_metrics',
    version='1.0',
    packages=[
        'metrics'
    ],
    scripts=[
        'scripts/sonic_metricsd',
    ],
    license='Apache 2.0',
    author='SONiC Team',
    author_email='lnos-coders@linkedin.com',
    maintainer="lnos-coders",
    maintainer_email='lnos-coders@linkedin.com',
    description='SONiC metrics python scripts',
    install_requires = dependencies,
    package_data = {
        'metrics': ['data/critical_process_file.json']
    },
    include_package_data=True,
    classifiers=[
        'Intended Audience :: Developers',
        'Operating System :: Linux',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python',
    ]
)
