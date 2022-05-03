#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
                'numpy>=1.16.5',
                'aioinflux',
                'pandas',
                'astropy',
                'pyyaml',
                'tables', 
                'kafkit', ]

setup_requirements = [
                      'pip==19.2.3',
                      'bump2version==0.5.11',
                      'wheel==0.33.6',
                      'watchdog==0.9.0',
                      'flake8==3.7.8',
                      'coverage==4.5.4',
                      'twine',
                      'pytest-runner', ]

test_requirements = ['pytest>=3',
                     'pytest-asyncio',
                     'pytest-vcr',]

extra_requirements = {
    'dev': [
        'documenteer[pipelines]',
        'docutils<0.18'
    ]
}

setup(
    author="Simon Krughoff",
    author_email='krughoff@lsst.org',
    python_requires='>=3.5',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="Utility classes for working with the LSST EFD.",
    install_requires=requirements,
    license="MIT license",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords=['LSST', 'EFD'],
    name='lsst-efd-client',
    packages=find_packages(include=['lsst_efd_client', 'lsst_efd_client.*']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    extras_require=extra_requirements,
    url='https://github.com/lsst-sqre/lsst-efd-client',
    version='0.10.2',
    zip_safe=False,
)
