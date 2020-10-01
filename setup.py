import os
import github_watchman.__about__ as a
from setuptools import setup

with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'README.md')) as f:
    README = f.read()

setup(
    name='github-watchman',
    version=a.__version__,
    url=a.__uri__,
    license=a.__license__,
    classifiers=[
        'Intended Audience :: Information Technology',
        'Topic :: Security',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    author=a.__author__,
    author_email=a.__email__,
    long_description=README,
    long_description_content_type='text/markdown',
    description=a.__summary__,
    install_requires=[
        'requests',
        'colorama',
        'termcolor',
        'PyYAML',
    ],
    packages=['github_watchman'],
    include_package_data=True,
    package_data={
            "": ["*.yml", "*.yaml"],
        },
    entry_points={
        'console_scripts': ['github-watchman=github_watchman:main']
    }
)
