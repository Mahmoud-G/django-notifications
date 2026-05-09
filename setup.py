#!/usr/bin/env python
# -*- coding: utf-8 -*-
''' Django notification setup file for pip package '''
import ast
import re

from setuptools import setup


_version_re = re.compile(r'__version__\s+=\s+(.*)')  # pylint: disable=invalid-name

with open('notifications/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(  # pylint: disable=invalid-name
        f.read().decode('utf-8')).group(1)))


setup(
    name='django-notifications-hq',
    version=version,
    description='GitHub notifications alike app for Django.',
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    author='django-notifications team',
    author_email='yang@yangyubo.com',
    url='http://github.com/django-notifications/django-notifications',
    install_requires=[
        'django>=4.2',
        'django-model-utils>=3.1.0',
        'swapper',
    ],
    packages=[
        'notifications',
        'notifications.base',
        'notifications.templatetags',
        'notifications.migrations',
    ],
    include_package_data=True,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 4.2',
        'Framework :: Django :: 5.0',
        'Framework :: Django :: 5.1',
        'Framework :: Django :: 5.2',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Topic :: Utilities',
    ],
    keywords='django notifications github action event stream',
    license='MIT',
    python_requires='>=3.9',
)
