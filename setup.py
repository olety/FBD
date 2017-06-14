from setuptools import setup


def readme():
    with open('README.md', 'r') as f:
        return f.read()


setup(
    name='fbd',
    version='0.0.2b2',
    description='Facebook data gatherer and analyzer',
    long_description=readme(),
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Topic :: Other/Nonlisted Topic'
    ],
    url='https://github.com/olety/FBD',
    author='Oleksii Kyrylchuk',
    author_email='olkyrylchuk@gmail.com',
    license='MIT',
    packages=['fbd'],
    scripts=['bin/fbd-gather'],
    install_requires=[
        'setuptools',
        'SQLAlchemy',
        'alembic',
        'requests',
        'async_timeout',
        'gmplot',
        'bokeh',
        'tqdm',
        'numpy',
        'geopy',
        'matplotlib',
        'aiohttp',
        'python_dateutil',
    ],
    include_package_data=True,
    zip_safe=False,
)
