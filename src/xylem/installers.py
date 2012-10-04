# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Willow Garage, Inc. nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

# Author Tully Foote/tfoote@willowgarage.com, Ken Conley/kwc@willowgarage.com

from __future__ import print_function

from .os_detect import OsDetect
from .core import InvalidData

# use OsDetect.get_version() for OS version key
TYPE_VERSION = 'version'
# use OsDetect.get_codename() for OS version key
TYPE_CODENAME = 'codename'

# kwc: InstallerContext is basically just a bunch of dictionaries with
# defined lookup methods.  It really encompasses two facets of a
# xylem configuration: the pluggable nature of installers and
# platforms, as well as the resolution of the operating system for a
# specific machine.  It is possible to decouple those two notions,
# though there are some touch points over how this interfaces with the
# .os_detect library, i.e. how platforms can tweak these
# detectors and how the higher-level APIs can override them.
class InstallerContext(object):
    """
    :class:`InstallerContext` manages the context of execution for xylem as it
    relates to the installers, OS detectors, and other extensible
    APIs.
    """
    
    def __init__(self, os_detect=None):
        """
        :param os_detect: (optional)
        :class:`.os_detect.OsDetect` instance to use for
          detecting platforms.  If `None`, default instance will be
          used.
        """
        # platform configuration
        self.installers = {}
        self.os_installers = {}
        self.default_os_installer = {}

        # stores configuration of which value to use for the OS version key (version number or codename)
        self.os_version_type = {}

        # OS detection and override
        if os_detect is None:
            os_detect = OsDetect()
        self.os_detect = os_detect
        self.os_override = None

        self.verbose = False
        
    def set_verbose(self, verbose):
        self.verbose = verbose
        
    def set_os_override(self, os_name, os_version):
        """
        Override the OS detector with *os_name* and *os_version*.  See
        :meth:`InstallerContext.detect_os`.

        :param os_name: OS name value to use, ``str``
        :param os_version: OS version value to use, ``str``
        """
        if self.verbose:
            print("overriding OS to [%s:%s]"%(os_name, os_version))
        self.os_override = os_name, os_version

    def get_os_version_type(self, os_name):
        return self.os_version_type.get(os_name, TYPE_VERSION)

    def set_os_version_type(self, os_name, version_type):
        if version_type not in (TYPE_VERSION, TYPE_CODENAME):
            raise ValueError("version type not TYPE_VERSION or TYPE_CODENAME")
        self.os_version_type[os_name] = version_type
        
    def get_os_name_and_version(self):
        """
        Get the OS name and version key to use for resolution and
        installation.  This will be the detected OS name/version
        unless :meth:`InstallerContext.set_os_override()` has been
        called.

        :returns: (os_name, os_version), ``(str, str)``
        """
        if self.os_override:
            return self.os_override
        else:
            os_name = self.os_detect.get_name()
            if self.get_os_version_type(os_name) == TYPE_CODENAME:
                os_version = self.os_detect.get_codename()
            else:
                os_version = self.os_detect.get_version()
            return os_name, os_version
        
    def get_os_detect(self):
        """
        :returns os_detect: :class:`OsDetect` instance used for
          detecting platforms.
        """
        return self.os_detect

    def set_installer(self, installer_key, installer):
        """
        Set the installer to use for *installer_key*.  This will
        replace any existing installer associated with the key.
        *installer_key* should be the same key used for the
        ``xylem.yaml`` package manager key.  If *installer* is
        ``None``, this will delete any existing associated installer
        from this context.

        :param installer_key: key/name to associate with installer, ``str``
        :param installer: :class:`Installer` implementation, ``class``.
        :raises: :exc:`TypeError` if *installer* is not a subclass of
          :class:`Installer`
        """
        if installer is None:
            del self.installers[installer_key]
            return
        if not isinstance(installer, Installer):
            raise TypeError("installer must be a instance of Installer")
        if self.verbose:
            print("registering installer [%s]"%(installer_key))
        self.installers[installer_key] = installer
        
    def get_installer(self, installer_key):
        """
        :returns: :class:`Installer` class associated with *installer_key*.
        :raises: :exc:`KeyError` If not associated installer
        :raises: :exc:`InstallFailed` If installer cannot produce an install command (e.g. if installer is not installed)
        """
        return self.installers[installer_key]

    def get_installer_keys(self):
        """
        :returns: list of registered installer keys
        """
        return self.installers.keys()

    def get_os_keys(self):
        """
        :returns: list of OS keys that have registered with this context, ``[str]``
        """
        return self.os_installers.keys()
    
    def add_os_installer_key(self, os_key, installer_key):
        """
        Register an installer for the specified OS.  This will fail
        with a :exc:`KeyError` if no :class:`Installer` can be found
        with the associated *installer_key*.
        
        :param os_key: Key for OS
        :param installer_key: Key for installer to add to OS
        :raises: :exc:`KeyError`: if installer for *installer_key*
          is not set.
        """
        # validate, will throw KeyError
        self.get_installer(installer_key)
        if self.verbose:
            print("add installer [%s] to OS [%s]"%(installer_key, os_key))
        if os_key in self.os_installers:
            self.os_installers[os_key].append(installer_key)
        else:
            self.os_installers[os_key] = [installer_key]

    def get_os_installer_keys(self, os_key):
        """
        Get list of installer keys registered for the specified OS.
        These keys can be resolved by calling
        :meth:`InstallerContext.get_installer`.
        
        :param os_key: Key for OS
        :raises: :exc:`KeyError`: if no information for OS *os_key* is registered.
        """
        if os_key in self.os_installers:
            return self.os_installers[os_key][:]
        else:
            raise KeyError(os_key)

    def set_default_os_installer_key(self, os_key, installer_key):
        """
        Set the default OS installer to use for OS.
        :meth:`InstallerContext.add_os_installer` must have previously
        been called with the same arguments.

        :param os_key: Key for OS
        :param installer_key: Key for installer to add to OS
        :raises: :exc:`KeyError`: if installer for *installer_key*
          is not set or if OS for *os_key* has no associated installers.
        """
        if not os_key in self.os_installers:
            raise KeyError("unknown OS: %s"%(os_key))
        if not installer_key in self.os_installers[os_key]:
            raise KeyError("installer [%s] is not associated with OS [%s]. call add_os_installer_key() first"%(installer_key, os_key))

        # validate, will throw KeyError
        self.get_installer(installer_key)
        if self.verbose:
            print("set default installer [%s] for OS [%s]"%(installer_key, os_key))
        self.default_os_installer[os_key] = installer_key

    def get_default_os_installer_key(self, os_key):
        """
        Get the default OS installer key to use for OS, or ``None`` if
        there is no default.

        :param os_key: Key for OS
        :returns: :class:`Installer`
        :raises: :exc:`KeyError`: if no information for OS *os_key* is registered.
        """
        if not os_key in self.os_installers:
            raise KeyError("unknown OS: %s"%(os_key))
        try:
            return self.default_os_installer[os_key]
        except KeyError:
            return None

class Installer(object):
    """
    The :class:`Installer` API is designed around opaque *resolved*
    parameters. These parameters can be any type of sequence object,
    but they must obey set arithmetic.  They should also implement
    ``__str__()`` methods so they can be pretty printed.
    """

    def is_installed(self, resolved_item):
        """
        :param resolved: resolved installation item. NOTE: this is a single item,
          not a list of items like the other APIs, ``opaque``.
        :returns: ``True`` if all of the *resolved* items are installed on
          the local system
        """
        raise NotImplementedError("is_installed", resolved_item) 
        
    def get_install_command(self, resolved, interactive=True, reinstall=False):
        """
        :param resolved: list of resolved installation items, ``[opaque]``
        :param interactive: If `False`, disable interactive prompts,
          e.g. Pass through ``-y`` or equivalant to package manager.
        :param reinstall: If `True`, install everything even if already installed
        """
        raise NotImplementedError("get_package_install_command", resolved, interactive, reinstall)

    def get_remove_command(self, resolved, interactive=True):
        commands = self.get_install_command(resolved, reinstall=True,
            interactive=interactive)
        # TODO: write individual cases for various package management
        # tools.
        return [['remove' if part == 'install' else part for part in cmd]
                for cmd in commands]

    def get_depends(self, xylem_args): 
        """ 
        :returns: list of dependencies on other xylem keys.  Only
          necessary if the package manager doesn't handle
          dependencies.
        """
        return [] # Default return empty list

    def resolve(self, xylem_args_dict):
        """
        :param xylem_args_dict: argument dictionary to the xylem rule for this package manager
        :returns: [resolutions].  resolved objects should be printable to a user, but are otherwise opaque.
        """
        raise NotImplementedError("Base class resolve", xylem_args_dict)

    def unique(self, *resolved_rules):
        """
        Combine the resolved rules into a unique list.  This
        is meant to combine the results of multiple calls to
        :meth:`PackageManagerInstaller.resolve`.

        Example::

            resolved1 = installer.resolve(args1)
            resolved2 = installer.resolve(args2)
            resolved = installer.unique(resolved1, resolved2)

        :param *resolved_rules: resolved arguments.  Resolved
          arguments must all be from this :class:`Installer` instance.
        """
        raise NotImplementedError("Base class unique", resolved_rules)
    
class PackageManagerInstaller(Installer):
    """
    General form of a package manager :class:`Installer`
    implementation that assumes:

     - installer xylem args spec is a list of package names stored with the key "packages"
     - a detect function exists that can return a list of packages that are installed

    Also, if *supports_depends* is set to ``True``:
    
     - installer xylem args spec can also include dependency specification with the key "depends"
    """

    def __init__(self, detect_fn, supports_depends=False):
        """
        :param detect_fn: function that checks whether every member of
                          a list of sytem packages is installed
        :param supports_depends: package manager supports dependency key
        """
        self.detect_fn = detect_fn
        self.supports_depends = supports_depends

    def resolve(self, xylem_args):
        """
        See :meth:`Installer.resolve()`
        """
        packages = None
        if type(xylem_args) == dict:
            packages = xylem_args.get("packages", [])
            if type(packages) == type("string"):
                packages = packages.split()
        elif type(xylem_args) == type('str'):
            packages = xylem_args.split(' ')
        elif type(xylem_args) == list:
            packages = xylem_args
        else:
            raise InvalidData("Invalid xylem args: %s"%(xylem_args))
        return packages

    def unique(self, *resolved_rules):
        """
        See :meth:`Installer.unique()`
        """
        s = set()
        for resolved in resolved_rules:
            s.update(resolved)
        return sorted(list(s))
        
    def get_packages_to_install(self, resolved, reinstall=False):
        if reinstall:
            return resolved
        if not resolved:
            return []
        else:
            return list(set(resolved) - set(self.detect_fn(resolved)))

    def is_installed(self, resolved_item):
        return not self.get_packages_to_install([resolved_item])

    def get_install_command(self, resolved, interactive=True, reinstall=False):
        raise NotImplementedError('subclasses must implement', resolved, interactive, reinstall)

    def get_depends(self, xylem_args): 
        """ 
        :returns: list of dependencies on other xylem keys.  Only
          necessary if the package manager doesn't handle
          dependencies.
        """
        if self.supports_depends and type(xylem_args) == dict:
            return xylem_args.get('depends', [])
        return [] # Default return empty list
