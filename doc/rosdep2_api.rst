.. _python_api:

xylem2 Python API
==================

.. module:: xylem2

**Experimental**: the xylem2 Python library is still unstable.

The :mod:`xylem` Python module supports both the `xylem`
command-line tool as well as libraries that wish to use xylem data
files to resolve dependencies.

As a developer, you may wish to extend :mod:`xylem` to add new OS
platforms or package managers.  Platforms are specified by registering
information on the :class:`InstallerContext`.  Package managers
generally extend the :class:`PackageManagerInstaller` implementation.

The :mod:`rospkg` library is used for OS detection.

Please consult the :ref:`Developers Guide <dev_guide>` for more
information on developing with the Python API.


.. contents:: Table of Contents
   :depth: 2

Exceptions
----------

.. autoclass:: InvalidData

Database Model
--------------

.. autoclass:: xylemDatabase
   :members:

.. autoclass:: xylemDatabaseEntry
   :members:

View Model
----------

.. autoclass:: xylemDefinition
   :members:

.. autoclass:: xylemView
   :members:

.. autoclass:: xylemLookup
   :members:

Loaders
-------

.. autoclass:: xylemLoader
   :members:

.. autoclass:: RosPkgLoader
   :members:

Installers
----------

.. autoclass:: InstallerContext
   :members:

.. autoclass:: Installer
   :members:

.. autoclass:: PackageManagerInstaller
   :members:

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

