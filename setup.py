from setuptools import setup, find_packages

setup(
    name='kalpana',
    version='2.0',
    description='A clean and very minimalistic word processor',
    url='https://github.com/kalpana-org/kalpana',
    author='nycz',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: X11 Applications :: Qt',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Text Editors :: Text Processing',
        'Topic :: Text Editors :: Word Processors'
    ],
    packages=find_packages(exclude=['thoughts', 'tests']),
    # install_requires=['PyQt5', 'PyYAML', 'pyenchant'],
    include_package_data=True,
    entry_points={
        'gui_scripts': [
            'kalpana=kalpana.kalpana:main'
        ]
    }
)
