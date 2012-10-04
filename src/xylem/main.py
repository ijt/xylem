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
from .installers import xylemInstaller
from .lookup import xylemLookup, ResolutionError
from .rospkg_loader import DEFAULT_VIEW_KEY
from .sources_list import update_sources_list, get_sources_cache_dir,\
    download_default_sources_list, SourcesListLoader, CACHE_INDEX,\
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

def _get_default_xylemLookup(options):
    """
    Helper routine for converting command-line options into
    appropriate xylemLookup instance.
    """
    os_override = convert_os_override_option(options.os_override)
    sources_loader = SourcesListLoader.create_default(sources_cache_dir=options.sources_cache_dir,
                                                      os_override=os_override,
                                                      verbose=options.verbose)
    lookup = xylemLookup.create_from_rospkg(sources_loader=sources_loader)
    lookup.verbose = options.verbose
    return lookup

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
    except ResolutionError as e:
        print("""
ERROR: %s

%s
"""%(e.args[0], e), file=sys.stderr)
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
    default_sources_cache = get_sources_cache_dir()

    parser = OptionParser(usage=_usage, prog='xylem')
    parser.add_option("--os", dest="os_override", default=None, 
                      metavar="OS_NAME:OS_VERSION", help="Override OS name and version (colon-separated), e.g. ubuntu:lucid")
    parser.add_option("-c", "--sources-cache-dir", dest="sources_cache_dir", default=default_sources_cache,
                      metavar='SOURCES_CACHE_DIR', help="Override %s"%(default_sources_cache))
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
    parser.add_option("-r", dest="robust", default=False, 
                      action="store_true", help="Continue installing despite errors.")
    parser.add_option("-a", "--all", dest="xylem_all", default=False, 
                      action="store_true", help="select all packages")
    parser.add_option("-n", dest="recursive", default=True, 
                      action="store_false", help="Do not consider implicit/recursive dependencies.  Only valid with 'keys', 'check', and 'install' commands.")

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

    if not command in ['init', 'update']:
        check_for_sources_list_init(options.sources_cache_dir)
    if command in _command_xylem_args:
        return _xylem_args_handler(command, parser, options, args)
    elif command in _command_no_args:
        return _no_args_handler(command, parser, options, args)        
    else:
        return _package_args_handler(command, parser, options, args)

def _no_args_handler(command, parser, options, args):
    if args:
        parser.error("command [%s] takes no arguments"%(command))
    else:
        return command_handlers[command](options)
    
def _xylem_args_handler(command, parser, options, args):

    # xylem keys as args
    if options.xylem_all:
        parser.error("-a, --all is not a valid option for this command")
    elif len(args) < 1:
        parser.error("Please enter arguments for '%s'"%command)
    else:
        return command_handlers[command](args, options)
    
def _package_args_handler(command, parser, options, args):
    # package or stack names as args.  have to convert stack names to packages.
    # - overrides to enable testing
    rospack = rospkg.RosPack()
    rosstack = rospkg.RosStack()
    lookup = _get_default_xylemLookup(options)
    loader = lookup.get_loader()
    
    if options.xylem_all:
        if args:
            parser.error("cannot specify additional arguments with -a")
        else:
            # let the loader filter the -a. This will take out some
            # packages that are catkinized (for now).
            args = loader.get_loadable_resources()
            not_found = []
    elif not args:
        parser.error("no packages or stacks specified")

    val = rospkg.expand_to_packages(args, rospack, rosstack)
    packages = val[0]
    not_found = val[1]
    if not_found:
        raise rospkg.ResourceNotFound(not_found[0], rospack.get_ros_paths())

    if 0 and not packages: # disable, let individual handlers specify behavior
        # possible with empty stacks
        print("No packages in arguments, aborting")
        return

    return command_handlers[command](lookup, packages, options)

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
    
def command_check(lookup, packages, options):
    verbose = options.verbose
    
    installer_context = create_default_installer_context(verbose=verbose)
    configure_installer_context_os(installer_context, options)
    installer = xylemInstaller(installer_context, lookup)

    uninstalled, errors = installer.get_uninstalled(packages, implicit=options.recursive, verbose=verbose)

    # pretty print the result
    if [v for k, v in uninstalled if v]:
        print("System dependencies have not been satisified:")
        for installer_key, resolved in uninstalled:
            if resolved:
                for r in resolved:
                    print("%s\t%s"%(installer_key, r))
    else:
        print("All system dependencies have been satisified")
    if errors:
        for package_name, ex in errors.items():
            if isinstance(ex, rospkg.ResourceNotFound):
                print("ERROR[%s]: resource not found [%s]"%(package_name, ex.args[0]), file=sys.stderr)
            else:
                print("ERROR[%s]: %s"%(package_name, str(ex)), file=sys.stderr)                
    if uninstalled:
        return 1
    else:
        return 0

def error_to_human_readable(error):
    if isinstance(error, rospkg.ResourceNotFound):
        return "Missing resource %s"%(str(error))
    elif isinstance(error, ResolutionError):
        return str(error.args[0])
    else:
        return str(error)
    
def command_install(packages, options):
    installer, _, _, _, _ = get_default_installer()
    resolved_pairs, invalid_key_errors, _ = resolve(packages, options)
    for _, resolved_pkgs in resolved_pairs:
        commands = installer.get_install_command(resolved_pkgs)
        for c in commands:
            subprocess.call(c)

    if invalid_key_errors:
        return 1 # error exit code

def command_remove(packages, options):
    installer, _, _, _, _ = get_default_installer()
    resolved_pairs, invalid_key_errors, _ = resolve(packages, options)
    for _, resolved_pkgs in resolved_pairs:
        commands = installer.get_remove_command(resolved_pkgs)
        for c in commands:
            subprocess.call(c)

    if invalid_key_errors:
        return 1 # error exit code

def _compute_depdb_output(lookup, packages, options):
    installer_context = create_default_installer_context(verbose=options.verbose)
    os_name, os_version = _detect_os(installer_context, options)
    
    output = "xylem dependencies for operating system %s version %s "%(os_name, os_version)
    for stack_name in stacks:
        output += "\nSTACK: %s\n"%(stack_name)
        view = lookup.get_stack_xylem_view(stack_name)
        for xylem in view.keys():
            definition = view.lookup(xylem)
            resolved = resolve_definition(definition, os_name, os_version)
            output = output + "<<<< %s -> %s >>>>\n"%(xylem, resolved)
    return output
    
def command_db(options):
    # exact same setup logic as command_resolve, should possibly combine
    lookup = _get_default_xylemLookup(options)
    installer_context = create_default_installer_context(verbose=options.verbose)
    configure_installer_context_os(installer_context, options)
    os_name, os_version = installer_context.get_os_name_and_version()
    try:
        installer_keys = installer_context.get_os_installer_keys(os_name)
        default_key = installer_context.get_default_os_installer_key(os_name)
    except KeyError:
        raise UnsupportedOs(os_name, installer_context.get_os_keys())
    installer = installer_context.get_installer(default_key)

    print("OS NAME: %s"%os_name)
    print("OS VERSION: %s"%os_version)
    errors = []
    print("DB [key -> resolution]")
    # db does not leverage the resource-based API
    view = lookup.get_xylem_view(DEFAULT_VIEW_KEY, verbose=options.verbose)
    for xylem_name in view.keys():
        try:
            d = view.lookup(xylem_name)
            inst_key, rule = d.get_rule_for_platform(os_name, os_version, installer_keys, default_key)
            resolved = installer.resolve(rule)
            resolved_str = " ".join(resolved)
            print ("%s -> %s"%(xylem_name, resolved_str))
        except ResolutionError as e:
            errors.append(e)

    #TODO: add command-line option for users to be able to see this.
    #This is useful for platform bringup, but useless for most users
    #as the xylem db contains numerous, platform-specific keys.
    if 0: 
        for error in errors:
            print("WARNING: %s"%(error_to_human_readable(error)), file=sys.stderr)

def _print_lookup_errors(lookup):
    for error in lookup.get_errors():
        if isinstance(error, rospkg.ResourceNotFound):
            print("WARNING: unable to locate resource %s"%(str(error.args[0])), file=sys.stderr)
        else:
            print("WARNING: %s"%(str(error)), file=sys.stderr)

def command_resolve(args, options):
    resolved_pairs, invalid_key_errors, _ = resolve(args, options)

    for rule_installer, resolved in resolved_pairs:
        print("#%s"%(rule_installer))
        print (" ".join([str(r) for r in resolved]))

    if invalid_key_errors:
        return 1 # error exit code

def resolve(args, options):
    """
    Resolve os-specific package names from xylem package names.

    :returns: resolved_dict, invalid_key_errors, lookup_errors
    """
    lookup = _get_default_xylemLookup(options)
    installer_context = create_default_installer_context(verbose=options.verbose)
    configure_installer_context_os(installer_context, options)

    installer, installer_keys, default_key, \
            os_name, os_version = get_default_installer(installer_context=installer_context,
                                                        verbose=options.verbose)
    invalid_key_errors = []
    resolved_pairs = []
    for xylem_name in args:
        if len(args) > 1:
            print("#xylem[%s]"%xylem_name)

        view = lookup.get_xylem_view(DEFAULT_VIEW_KEY, verbose=options.verbose)
        try:
            d = view.lookup(xylem_name)
        except KeyError as e:
            print("ERROR: no xylem rule for %s"%(error), file=sys.stderr)        
            invalid_key_errors.append(e)
            continue
        rule_installer, rule = d.get_rule_for_platform(os_name, os_version, installer_keys, default_key)

        installer = installer_context.get_installer(rule_installer)
        resolved = installer.resolve(rule)
        resolved_pairs.append((rule_installer, resolved))

    for error in lookup.get_errors():
        print("WARNING: %s"%(error_to_human_readable(error)), file=sys.stderr)

    return resolved_pairs, invalid_key_errors, lookup.get_errors()

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
    'db': command_db,
    'check': command_check,
    'install': command_install,
    'remove': command_remove,
    # TODO: Rename this to "lookup".
    'resolve': command_resolve,
    'init': command_init,
    'update': command_update,
    }

# commands that accept args
_command_xylem_args = ['install', 'remove', 'resolve']

# commands that take no args
_command_no_args = ['update', 'init', 'db']

_commands = command_handlers.keys()



