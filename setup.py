from setuptools import setup

setup(name='fbd',
      version='0.0.1',
      description='Facebook data gatherer and analyzer',
      url='https://github.com/olety/FBD',
      author='Oleksii Kyrylchuk',
      author_email='olkyrylchuk@gmail.com',
      license='MIT',
      packages=['fbd'],
      install_requires=['requests', 'gmplot', 'geocoder', 'alembic', 'bokeh', 'matplotlib',
                        'tqdm', 'setuptools', 'SQLAlchemy', 'numpy', 'python_dateutil'],
      include_package_data=True,
      zip_safe=False)
