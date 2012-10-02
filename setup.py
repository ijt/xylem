from distutils.core import setup

import sys
sys.path.insert(0, 'src')

from xylem2 import __version__

setup(name='xylem',
      version= __version__,
      packages=['xylem2', 'xylem2.platforms'],
      package_dir = {'':'src'},
#      data_files=[('man/man1', ['doc/man/xylem.1'])],
      install_requires = ['rospkg', 'PyYAML>=3.1'],
      setup_requires = ['nose>=1.0'],
      test_suite = 'nose.collector',
      test_requires = ['mock'],
      scripts = [
        'scripts/xylem',
        'scripts/xylem-gbp-brew',
        'scripts/xylem-source',
        ],
      author = "Tully Foote, Ken Conley", 
      author_email = "foote@willowgarage.com, kwc@willowgarage.com",
      url = "http://www.ros.org/wiki/xylem",
      download_url = "http://pr.willowgarage.com/downloads/xylem/", 
      keywords = ["ROS"],
      classifiers = [
        "Programming Language :: Python", 
        "License :: OSI Approved :: BSD License" ],
      description = "xylem system dependency installation tool", 
      long_description = """\
Command-line tool for installing system dependencies on a variety of platforms.
""",
      license = "BSD"
      )
