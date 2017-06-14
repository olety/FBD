from setuptools import setup


def readme():
    with open('README.md', 'r') as f:
        return f.read()


setup(
    name='fbd',
    version='0.0.1b34',
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
    install_requires=['requests', 'gmplot', 'geocoder', 'alembic', 'bokeh', 'matplotlib',
                      'tqdm', 'setuptools', 'SQLAlchemy', 'numpy', 'python_dateutil'],
    include_package_data=True,
    zip_safe=False)
