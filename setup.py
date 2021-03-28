from setuptools import setup

from build_magic import __version__ as version

setup(
    name='build-magic',
    version=version,
    packages=[
        'build_magic',
    ],
    url='https://github.com/cmmorrow/build-magic',
    license='MIT',
    author='Chris Morrow',
    author_email='cmmorrow@gmail.com',
    description='A general purpose build/install/deploy tool.',
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'build-magic=build_magic.cli:build_magic',
        ],
    },
    install_requires=[
        'blessings',
        'click',
        'colorama',
        'jsonschema',
        'docker',
        'paramiko',
        'python-vagrant',
        'PyYAML',
        'scp',
    ],
    tests_require=[
        'pytest',
        'freezegun',
    ],
    # extras_require={
    #     'tests': ['tests'],
    # },
    classifers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Environment :: Console :: Curses',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: MacOS',
        'Operating System :: Microsoft :: Windows :: Windows 10',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Software Development',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Testing',
        'Topic :: Utilities',
    ],
)
