import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README')).read()
CHANGES = open(os.path.join(here, 'CHANGES')).read()

requires = [
    'pymongo',
]

setup(name='nosqlalchemy',
      version='0.9.2',
      description='Define loosly ordered schema for mongodb documents.',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        ],
      author='Jared Rodriguez',
      author_email='jared@blacknode.net',
      url='http://blog.blacknode.net',
      keywords='mongodb mongo nosql',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      test_suite='nosqlalchemy.tests',
      install_requires=requires,
      entry_points="""
      """,
      )
