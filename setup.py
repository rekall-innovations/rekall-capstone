#!/usr/bin/env python
"""This builds the capstone python extension using python's own build system:

This version does not use or need CMake - this means it will build on windows
only with the MSVC compilers for python
(https://www.microsoft.com/en-us/download/details.aspx?id=44266)
"""

import glob
import os
import platform
import shutil
import subprocess

from distutils import dir_util
from setuptools import setup, Command, Extension
from setuptools.command.sdist import sdist
from setuptools.command.build_ext import build_ext


SYSTEM = platform.system().lower()
VERSION = '3.0.4.post2'


def get_sources():
    """Returns a list of C source files that should be compiled to
    create the library.
    """
    result = []
    for root, _, files in os.walk("./src/"):
        for name in files:
            if name.endswith(".c"):
                result.append(os.path.join(root, name))

    return result


class LibraryBuilder(build_ext):
    """This builds the capstone dll.

    We just use setuptools normal builder for shared objects (which python
    extensions are.
    """
    def get_export_symbols(self, ext):
        """We do not need to export anything specific."""
        return []

    def get_ext_filename(self, _):
        """Get the filename of the final shared object."""
        # Capston specifically looks for these by name differently on each OS.
        if SYSTEM == "windows":
            return "capstone/capstone.dll"

        if SYSTEM == "darwin":
            return "capstone/libcapstone.dylib"

        return "capstone/libcapstone.so"


class SDistCommand(sdist):
    """Reshuffle files for distribution."""

    def run(self):
        source_path = "capstone_source"

        # Capstone submodule is not there, probably because this has been
        # freshly checked out.
        if not os.access(os.path.join(source_path, "bindings"), os.R_OK):
            subprocess.check_call(["git", "submodule", "init"])
            subprocess.check_call(["git", "submodule", "update"])

        self.copy_sources()
        return sdist.run(self)

    @staticmethod
    def copy_sources():
        """Copy the C sources into the source directory.

        This rearranges the source files under the python distribution
        directory.
        """
        result = []

        try:
            dir_util.remove_tree("src/")
        except (IOError, OSError):
            pass

        try:
            dir_util.remove_tree("capstone/")
        except (IOError, OSError):
            pass

        dir_util.copy_tree("capstone_source/arch", "src/arch/")
        dir_util.copy_tree("capstone_source/include", "src/include/")
        dir_util.copy_tree(
            "capstone_source/bindings/python/capstone", "capstone")

        result.extend(glob.glob("capstone_source/*.[ch]"))
        result.extend(glob.glob("capstone_source/LICENSE*"))
        result.extend(glob.glob("capstone_source/README"))
        result.extend(glob.glob("capstone_source/*.TXT"))
        result.extend(glob.glob("capstone_source/RELEASE_NOTES"))

        for filename in result:
            outpath = os.path.join("./src/", os.path.basename(filename))
            print "%s -> %s" % (filename, outpath)
            shutil.copy(filename, outpath)


class CleanCommand(Command):
    description = ("custom clean command that forcefully removes "
                   "dist/build directories")
    user_options = []
    def initialize_options(self):
        self.cwd = None
    def finalize_options(self):
        self.cwd = os.getcwd()
    def run(self):
        if os.getcwd() != self.cwd:
            raise RuntimeError('Must be in package root: %s' % self.cwd)

        for dirname in ['./build', './dist', 'rekall_yara.egg-info']:
            shutil.rmtree(dirname, True)

class UpdateCommand(Command):
    """Update capstone source.

    This is normally only run by packagers to make a new release.
    """
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        subprocess.check_call(["git", "stash"], cwd="capstone_source")

        subprocess.check_call(["git", "submodule", "init"])
        subprocess.check_call(["git", "submodule", "update"])

        print("Updating capstone source")
        subprocess.check_call(["git", "reset", "--hard"], cwd="capstone_source")
        subprocess.check_call(["git", "clean", "-x", "-f", "-d"],
                              cwd="capstone_source")
        subprocess.check_call(["git", "checkout", "master"],
                              cwd="capstone_source")
        subprocess.check_call(["git", "pull"], cwd="capstone_source")


include_dirs = ["src", "src/include", "src/arch"]
compile_args = []
if SYSTEM == "windows":
    include_dirs.append("windows")

    # The MSVC2010 compiler can not handle optimization properly. It breaks with
    # an error "fatal error C1063: compiler limit : compiler stack overflow" so
    # we just switch optimization off.
    compile_args.append("/Od")


setup(
    provides=['capstone'],
    packages=['capstone'],
    name='rekall-capstone',
    version=VERSION,
    author='Nguyen Anh Quynh',
    author_email='aquynh@gmail.com',
    description='Capstone disassembly engine',
    url='http://www.capstone-engine.org',
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],
    requires=['ctypes'],
    cmdclass=dict(
        sdist=SDistCommand,
        clean=CleanCommand,
        build_ext=LibraryBuilder,
        update=UpdateCommand,
    ),
    zip_safe=False,
    ext_modules=[
        Extension(
            "capstone.libcapstone",
            get_sources(),
            define_macros=[
                ('CAPSTONE_X86_ATT_DISABLE_NO', 1),
                ('CAPSTONE_DIET_NO', 1),
                ('CAPSTONE_X86_REDUCE_NO', 1),
                ('CAPSTONE_HAS_ARM', 1),
                ('CAPSTONE_HAS_ARM64', 1),
                ('CAPSTONE_HAS_MIPS', 1),
                ('CAPSTONE_HAS_POWERPC', 1),
                ('CAPSTONE_HAS_SPARC', 1),
                ('CAPSTONE_HAS_SYSZ', 1),
                ('CAPSTONE_HAS_X86', 1),
                ('CAPSTONE_HAS_XCORE', 1),
                ('CAPSTONE_USE_SYS_DYN_MEM', 1),
                ('CAPSTONE_SHARED', 1)],
            include_dirs=include_dirs,
            extra_compile_args=compile_args)
    ],
)
