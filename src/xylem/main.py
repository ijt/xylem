#!/usr/bin/env python
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

# Author Tully Foote/tfoote@willowgarage.com

"""
Command-line interface to xylem library
"""

from __future__ import print_function

import exceptions
import os
import sys
import subprocess
import traceback
import urllib2

from optparse import OptionParser

import rospkg

from . import create_default_installer_context
from . import __version__
from .core import xylemInternalError, UnsupportedOs, InvalidData
from .sources_list import update_sources_list, get_sources_cache_dir,\
    download_default_sources_list, CACHE_INDEX,\
    get_sources_list_dir, get_default_sources_list_file,\
    DEFAULT_SOURCES_LIST_URL

class UsageError(Exception):
    pass

_usage = """usage: xylem [options] <command> <args>

Commands:

xylem check <package>...
  check if the package is installed.

xylem install <packages>...
  install some packages.

xylem db
  generate the dependency database and print it to the console.

xylem init
  initialize xylem sources in /etc/ros/xylem.  May require sudo.

xylem remove <packages>...
  uninstall packages

xylem resolve <packages>
  resolve <packages> to system dependencies
  
xylem update
  update the local xylem database based on the xylem sources.
"""

def xylem_main(args=None):
    if args is None:
        args = sys.argv[1:]
    try:
        exit_code = _xylem_main(args)
        if exit_code not in [0, None]:
            sys.exit(exit_code)
    except rospkg.ResourceNotFound as e:
        print("""
ERROR: xylem cannot find all required resources to answer your query
%s
"""%(error_to_human_readable(e)), file=sys.stderr)
        sys.exit(1)
    except UsageError as e:
        print(_usage, file=sys.stderr)
        print("ERROR: %s"%(str(e)), file=sys.stderr)
        sys.exit(os.EX_USAGE)
    except xylemInternalError as e:
        print("""
ERROR: xylem experienced an internal error.
Please go to the xylem page [1] and file a bug report with the message below.
[1] : http://www.ros.org/wiki/xylem

%s
"""%(e.message), file=sys.stderr)
        sys.exit(1)
    except UnsupportedOs as e:
        print("Unsupported OS: %s\nSupported OSes are [%s]"%(e.args[0], ', '.join(e.args[1])), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print("""
ERROR: xylem experienced an internal error: %s
Please go to the xylem page [1] and file a bug report with the stack trace below.
[1] : http://www.ros.org/wiki/xylem

%s
"""%(e, traceback.format_exc(e)), file=sys.stderr)
        sys.exit(1)
        
def check_for_sources_list_init(sources_cache_dir):
    """
    Check to see if sources list and cache are present.
    *sources_cache_dir* alone is enough to pass as the user has the
    option of passing in a cache dir.
    
    If check fails, tell user how to resolve and sys exit.
    """
    commands = []
    filename = os.path.join(sources_cache_dir, CACHE_INDEX)
    if os.path.exists(filename):
        return
    else:
        commands.append('xylem update')

    sources_list_dir = get_sources_list_dir()
    if not os.path.exists(sources_list_dir):
        commands.insert(0, 'sudo xylem init')
    else:
        filelist = [f for f in os.listdir(sources_list_dir) if f.endswith('.list')]    
        if not filelist:
            commands.insert(0, 'sudo xylem init')

    if commands:
        commands = '\n'.join(["    %s"%c for c in commands])
        print("""
ERROR: your xylem installation has not been initialized yet.  Please run:
        
%s
"""%(commands), file=sys.stderr)
        sys.exit(1)
    else:
        return True
    
def _xylem_main(args):
    # sources cache dir is our local database.  
    parser = OptionParser(usage=_usage, prog='xylem')
    parser.add_option("--os", dest="os_override", default=None,
                      metavar="OS_NAME:OS_VERSION", help="Override OS name and version (colon-separated), e.g. ubuntu:lucid")
    parser.add_option("--verbose", "-v", dest="verbose", default=False, 
                      action="store_true", help="verbose display")
    parser.add_option("--version", dest="print_version", default=False, 
                      action="store_true", help="print version and exit")
    parser.add_option("--reinstall", dest="reinstall", default=False, 
                      action="store_true", help="(re)install all dependencies, even if already installed")
    parser.add_option("--default-yes", "-y", dest="default_yes", default=False, 
                      action="store_true", help="Tell the package manager to default to y or fail when installing")
    parser.add_option("--simulate", "-s", dest="simulate", default=False, 
                      action="store_true", help="Simulate install")
    #parser.add_option("-r", dest="robust", default=False, 
    #                  action="store_true", help="Continue installing despite errors.")

    options, args = parser.parse_args(args)
    if options.print_version:
        print(__version__)
        sys.exit(0)

    if len(args) == 0:
        parser.error("Please enter a command")
    command = args[0]
    if not command in _commands:
        parser.error("Unsupported command %s."%command)
    args = args[1:]

    if command in _command_xylem_args:
        return _args_handler(command, parser, options, args)
    elif command in _command_no_args:
        return _no_args_handler(command, parser, options, args)        

def _no_args_handler(command, parser, options, args):
    if args:
        parser.error("command [%s] takes no arguments"%(command))
    else:
        return command_handlers[command](options)
    
def _args_handler(command, parser, options, args):
    # package keys as args
    if not args:
        parser.error("Please enter arguments for '%s'"%command)
    else:
        return command_handlers[command](args, options)

def convert_os_override_option(options_os_override):
    """
    Convert os_override option flag to ``(os_name, os_version)`` tuple, or
    ``None`` if not set

    :returns: ``(os_name, os_version)`` tuple if option is set, ``None`` otherwise
    :raises: :exc:`UsageError` if option is not set properly
    """
    if not options_os_override:
        return None
    val = options_os_override
    if not ':' in val:
        raise UsageError("OS override must be colon-separated OS_NAME:OS_VERSION, e.g. ubuntu:maverick")
    os_name = val[:val.find(':')]
    os_version = val[val.find(':')+1:]
    return os_name, os_version
    
def configure_installer_context_os(installer_context, options):
    """
    Override the OS detector in *installer_context* if necessary.

    :raises: :exc:`UsageError` If user input options incorrectly
    """
    os_override = convert_os_override_option(options.os_override)
    if os_override is not None:
        installer_context.set_os_override(*os_override)
    
def command_init(options):
    try:
        data = download_default_sources_list()
    except urllib2.URLError as e:
        print("ERROR: cannot download default sources list from:\n%s\nWebsite may be down."%(DEFAULT_SOURCES_LIST_URL))
        return 4
    # reuse path variable for error message
    path = get_sources_list_dir()
    try:
        if not os.path.exists(path):
            os.makedirs(path)
        path = get_default_sources_list_file()
        if os.path.exists(path):
            print("Default sources list file already exists:\n\t%s\nPlease delete if you wish to re-initialize"%(path))
            return 0
        with open(path, 'w') as f:
            f.write(data)
        print("Wrote %s"%(path))
        print("Recommended: please run\n\n\txylem update\n")
    except IOError as e:
        print("ERROR: cannot create %s:\n\t%s"%(path, e), file=sys.stderr)
        return 2
    except OSError as e:
        print("ERROR: cannot create %s:\n\t%s\nPerhaps you need to run 'sudo xylem init' instead"%(path, e), file=sys.stderr)
        return 3
    
def command_update(options):
    def update_success_handler(data_source):
        print("Hit %s"%(data_source.url))
    def update_error_handler(data_source, exc):
        print("ERROR: unable to process source [%s]:\n\t%s"%(data_source.url, exc), file=sys.stderr)
    sources_list_dir = get_sources_list_dir()
    filelist = [f for f in os.listdir(sources_list_dir) if f.endswith('.list')]    
    if not filelist:
        print("ERROR: no data sources in %s\n\nPlease initialize your xylem with\n\n\tsudo xylem init\n"%sources_list_dir, file=sys.stderr)
        return 1
    try:
        print("reading in sources list data from %s"%(sources_list_dir))
        update_sources_list(success_handler=update_success_handler,
                            error_handler=update_error_handler)
        print("updated cache in %s"%(get_sources_cache_dir()))
    except InvalidData as e:
        print("ERROR: invalid sources list file:\n\t%s"%(e), file=sys.stderr)
    except IOError as e:
        print("ERROR: error loading sources list:\n\t%s"%(e), file=sys.stderr)
    
def command_check(args, options):
    try:
        installer, _, _, _, _ = get_default_installer()
        for xylem_pkg in args:
            if not installer.detect_fn(resolve([xylem_pkg], options)):
                print("%s does not appear to be installed." % xylem_pkg)
                return 1

        print("All given packages appear to be installed.")
        return 0
    except exceptions.OSError:
        return 1

def error_to_human_readable(error):
    if isinstance(error, rospkg.ResourceNotFound):
        return "Missing resource %s"%(str(error))
    else:
        return str(error)
    
def command_install(packages, options):
    installer, _, _, _, _ = get_default_installer()
    for p in resolve(packages, options):
        commands = installer.get_install_command([p])
        for c in commands:
            subprocess.call(c)
    return 0

def command_remove(packages, options):
    installer, _, _, _, _ = get_default_installer()
    for p in resolve(packages, options):
        commands = installer.get_remove_command([p])
        for c in commands:
            subprocess.call(c)
    return 0

def _print_lookup_errors(lookup):
    for error in lookup.get_errors():
        if isinstance(error, rospkg.ResourceNotFound):
            print("WARNING: unable to locate resource %s"%(str(error.args[0])), file=sys.stderr)
        else:
            print("WARNING: %s"%(str(error)), file=sys.stderr)

def command_resolve(args, options):
    print(' '.join(resolve(args, options)))
    return 0

def resolve(args, options):
    """
    Resolve os-specific package names from xylem package names.

    :returns: list of system-specific package names
    """
    installer_context = create_default_installer_context(verbose=options.verbose)
    configure_installer_context_os(installer_context, options)
    installer, _, _, _, _ = get_default_installer(installer_context=installer_context,
                                                  verbose=options.verbose)
    return [syspkg for xpkg in args for syspkg in installer.resolve(xpkg)]

def get_default_installer(installer_context=None, verbose=False):
    """
    Based on the active OS and installer context configuration, get
    the installer to use and the necessary configuration state
    (installer keys, OS name/version).
    
    :returns: installer, installer_keys, default_key, os_name, os_version. 
    """
    if installer_context is None:
        installer_context = create_default_installer_context(verbose=verbose)

    os_name, os_version = installer_context.get_os_name_and_version()
    try:
        installer_keys = installer_context.get_os_installer_keys(os_name)
        default_key = installer_context.get_default_os_installer_key(os_name)
    except KeyError:
        raise UnsupportedOs(os_name, installer_context.get_os_keys())
    installer = installer_context.get_installer(default_key)
    return installer, installer_keys, default_key, os_name, os_version

command_handlers = {
    'check': command_check,
    'install': command_install,
    'remove': command_remove,
    # TODO: Rename this to "lookup".
    'resolve': command_resolve,
    'init': command_init,
    'update': command_update,
    }

# commands that accept args
_command_xylem_args = ['check', 'install', 'remove', 'resolve']

# commands that take no args
_command_no_args = ['update', 'init', 'db']

_commands = command_handlers.keys()



