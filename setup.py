
from setuptools import setup, find_packages

console_scripts = ['azove=azove.z:main', 'azovetool=tools.azovetool:main']

setup(name="azove",
      version='0',
      packages=find_packages("."),
      install_requires=[
          'six', 'leveldb', 'bitcoin', 'pysha3',
          'miniupnpc',
          'bottle', 'waitress'],
      entry_points=dict(console_scripts=console_scripts))
