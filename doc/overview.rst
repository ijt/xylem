Overview
========

Installing xylem
-----------------

xylem2 is available using pip or easy_install::

    sudo pip install -U xylem

or::

    sudo easy_install -U xylem rospkg



Setting up xylem
-----------------

xylem needs to be initialized and updated to use::

    sudo xylem init
    xylem update

``sudo xylem init`` will create a `sources list <sources_list>`_
directory in ``/etc/ros/xylem/sources.list.d`` that controls where
xylem gets its data from.

``xylem update`` reads through this sources list to initialize your
local database.

Updating xylem
---------------

You can update your xylem database by running::

    xylem update


Installating xylems
--------------------

xylem takes in the name of a ROS stack or package that you wish to
install the system dependencies for.

Common installation workflow::

    $ xylem check ros_comm
    All system dependencies have been satisified
    $ xylem install geometry

If you're worried about ``xylem install`` bringing in system
dependencies you don't want, you can run ``xylem install -s <args>``
instead to "simulate" the installation.  You will be able to see the
commands that xylem would have run.

Example::

    $ xylem install -s ros_comm
    #[apt] Installation commands:
      sudo apt-get install libapr1-dev
      sudo apt-get install libaprutil1-dev
      sudo apt-get install libbz2-dev
      sudo apt-get install liblog4cxx10-dev
      sudo apt-get install pkg-config
      sudo apt-get install python-imaging
      sudo apt-get install python-numpy
      sudo apt-get install python-paramiko
      sudo apt-get install python-yaml
    
You can also query xylem to find out more information about specific
dependencies::

    $ xylem keys roscpp
    pkg-config

    $ xylem resolve pkg-config
    pkg-config

    $ xylem keys geometry
    eigen
    apr
    glut
    python-sip
    python-numpy
    graphviz
    paramiko
    cppunit
    libxext
    log4cxx
    pkg-config

    $ xylem resolve eigen
    libeigen3-dev



For more information, please see the :ref:`command reference <xylem_usage>`.

