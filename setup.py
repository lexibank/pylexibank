from setuptools import setup, find_packages


setup(
    name='pylexibank',
    version='1.1.2.dev0',
    author='Robert Forkel',
    author_email='forkel@shh.mpg.de',
    description='Python library implementing the lexibank workbench',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    keywords='',
    license='Apache 2.0',
    url='https://github.com/lexibank/pylexibank',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'cldfbench.commands': [
            'lexibank=pylexibank.commands',
        ],
        'cldfbench.scaffold': [
            'lexibank=pylexibank.scaffold:LexibankTemplate'
        ],
    },
    platforms='any',
    python_requires='>=3.5',
    install_requires=[
        'cldfbench>=0.3',
        'csvw>=1.5.6',
        'clldutils>=2.8.0',
        'pycldf>=1.7.0',
        'attrs>=18.1.0',
        'pyglottolog>=2.0',
        'pyconcepticon>=2.1.0',
        'pyclts>=1.2.0',
        'segments>=2.0.2',
        'lingpy>=2.6.5',
        'appdirs',
        'requests',
        'termcolor',
        'gitpython',
        'tqdm',
        'xlrd',
        'prompt_toolkit>=1.0',
        'python-nexus',
    ],
    extras_require={
        'dev': ['flake8', 'wheel', 'twine'],
        'test': [
            'mock',
            'pytest>=3.6',
            'pytest-mock',
            'pytest-cov',
            'coverage>=4.2',
        ],
    },
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy'
    ],
)
