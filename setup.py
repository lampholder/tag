from distutils.core import setup

setup (
  name = 'Tag Server',
  version = '0.1',
  author = 'Thomas Lant',
  author_email = 'thomas.lant@gmail.com',
  packages = ['tag'],
  scripts = ['bin/tag-server'],
  license = 'LICENSE.txt',
  description = 'A simple web process for storing tags.',
  long_description = open('README.md').read(),
)
