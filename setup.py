import os

from setuptools import setup


def readme():
    with open(
            os.path.join(os.getcwd(), os.path.dirname(__file__), 'README.md'),
            'r') as readme:
        return readme.read()


setup(
    name='fbd',
    version='0.0.2b8',
    description='Facebook data gatherer and analyzer',
    long_description=readme(),
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Topic :: Other/Nonlisted Topic',
    ],
    url='https://github.com/olety/FBD',
    author='Oleksii Kyrylchuk',
    author_email='olkyrylchuk@gmail.com',
    license='MIT',
    packages=[
        'fbd',
    ],
    scripts=[
        'bin/fbd-gather',
    ],
    requires_python=3.6,
    install_requires=[
        'tqdm',
        'bokeh',
        'SQLAlchemy',
        'setuptools',
        'aiohttp',
        'geopy',
        'alembic',
        'numpy',
        'requests',
        'matplotlib',
        'gmplot',
        'async_timeout',
        'python_dateutil',
    ],
    include_package_data=True,
    zip_safe=False,
)
