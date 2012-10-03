xylem command reference
========================

.. _xylem_usage:

Synopsis
--------

**xylem** <*command*> [*options*] [*args*]

Description
-----------

The **xylem** command helps you install external dependencies in an
OS-independent manner.  For example, what Debian packages do you need
in order to get the OpenGL headers on Ubuntu? How about OS X? Fedora?
xylem can answer this question for your platform and install the
necessary package(s).

Run ``xylem -h`` or ``xylem <command> -h`` to access the built-in tool
documentation.
 
Commands
--------

**check <stacks-and-packages>...**

  Check if the dependencies of ROS package(s) have been met.

**db**

  Display the local xylem database.

**init**

  Initialize /etc/ros/sources.list.d/ configuration.  May require sudo.

**install <stacks-and-packages>...**

  Install dependencies for specified ROS packages.

**keys <stacks-and-packages>...**

  List the xylem keys that the ROS packages depend on.

**resolve <packages>...**

  Resolve <packages> to system dependencies

**update**

  Update the local xylem database based on the xylem sources.

**what-needs <packages>...**

  Print a list of packages that declare a xylem on (at least
  one of) <packages>

**where-defined <packages>...**

  Print a list of YAML files that declare a xylem on (at least
  one of) <packages>

Options
-------

**--os=OS_NAME:OS_VERSION**

  Override OS name and version (colon-separated), e.g. ubuntu:lucid
  
**-c SOURCES_CACHE_DIR, --sources-cache-dir=SOURCES_CACHE_DIR**

  Override default sources cache directory (local xylem database).
  
**-a, --all**

  Select all ROS packages.  Only valid for commands that take <stacks-and-packages> as arguments.

**-h, --help**

  Show usage information

**-v, --verbose**

  Enable verbose output

**--version**

  Print version and exit.

Install Options
---------------

**--reinstall**

  (re)install all dependencies, even if already installed

**-y, --default-yes**

  Tell the package manager to default to y or fail when installing

**-s, --simulate**

  Simulate install

**-r**

  Continue installing despite errors.

**-R**

  Install implicit/recursive dependencies.

