#! /usr/bin/env python
# encoding: utf-8

# Kupfer's main wscript description file for Waf, written by Ulrik Sverdrup
# may be distributed, changed, used, etc freely for any purpose

import os
import sys
try:
    from waflib import Configure, Options, Utils, Logs
except ImportError:
    print("You need to upgrade to Waf 1.6! See README.")
    sys.exit(1)

# the following two variables are used by the target "waf dist"
APPNAME="kupfer"
VERSION = "undefined"

def _get_git_version():
    """ try grab the current version number from git"""
    version = None
    if os.path.exists(".git"):
        try:
            version = os.popen("git describe").read().strip()
        except Exception as e:
            print(e)
    return version

def _read_git_version():
    """Read version from git repo, or from GIT_VERSION"""
    version = _get_git_version()
    if not version and os.path.exists("GIT_VERSION"):
        f = open("GIT_VERSION", "r")
        version = f.read().strip()
        f.close()
    if version:
        global VERSION
        VERSION = version

def _write_git_version():
    """ Write the revision to a file called GIT_VERSION,
    to grab the current version number from git when
    generating the dist tarball."""
    version = _get_git_version()
    if not version:
        return False
    version_file = open("GIT_VERSION", "w")
    version_file.write(version + "\n")
    version_file.close()
    return True


_read_git_version()

# these variables are mandatory ('/' are converted automatically)
top = '.'
out = 'build'

config_subdirs = "auxdata help"
build_subdirs = "auxdata data po help"

EXTRA_DIST = [
    #"waf",
    "GIT_VERSION",
]

def _tarfile_append_as(tarname, filename, destname):
    import tarfile
    tf = tarfile.TarFile.open(tarname, "a")
    try:
        tarinfo = tf.gettarinfo(name=filename, arcname=destname)
        tarinfo.uid = 0
        tarinfo.gid = 0
        tarinfo.uname = "root"
        tarinfo.gname = "root"
        with open(filename, "rb") as f:
            tf.addfile(tarinfo, f)
    finally:
        tf.close()

def gitdist(ctx):
    """Make the release tarball using git-archive"""
    import subprocess
    if not _write_git_version():
        raise Exception("No version")
    basename = "%s-%s" % (APPNAME, VERSION)
    outname = basename + ".tar"
    proc = subprocess.Popen(
        ["git", "archive", "--format=tar", "--prefix=%s/" % basename, "HEAD"],
        stdout=subprocess.PIPE)
    fd = os.open(outname, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o666)
    os.write(fd, proc.communicate()[0])
    os.close(fd)
    for distfile in EXTRA_DIST:
        _tarfile_append_as(outname, distfile, os.path.join(basename, distfile))
    subprocess.call(["xz", "-6e", outname])
    subprocess.call(["sha1sum", outname + ".xz"])

def dist(ctx):
    "The standard waf dist process"
    import Scripting
    _write_git_version()
    Scripting.g_gz = "gz"
    Scripting.dist(ctx)


def options(opt):
    # options for disabling pyc or pyo compilation
    opt.load("python")
    opt.load("gnu_dirs")
    opt.add_option('--nopyo',action='store_false',default=False,help='Do not install optimised compiled .pyo files [This is the default for Kupfer]',dest='pyo')
    opt.add_option('--pyo',action='store_true',default=False,help='Install optimised compiled .pyo files [Default:not install]',dest='pyo')
    opt.add_option('--no-runtime-deps',action='store_false',default=True,
            help='Do not check for any runtime dependencies',dest='check_deps')
    opt.recurse(config_subdirs)

def configure(conf):
    conf.load("python")
    try:
        conf.check_python_version((3, 5, 0))
    except Configure.ConfigurationError:
        if os.getenv("PYTHON"):
            raise
        Logs.pprint("NORMAL", "Looking for Python 3 instead")
        conf.env["PYTHON"] = ["python3"]
        conf.check_python_version((3, 5, 0))
    conf.load("gnu_dirs")

    conf.load("intltool")

    conf.env["KUPFER"] = Utils.subst_vars("${BINDIR}/kupfer", conf.env)
    conf.env["VERSION"] = VERSION
    conf.recurse(config_subdirs)

    # Setup PYTHONDIR so we install into $DATADIR
    conf.env["PYTHONDIR"] = Utils.subst_vars("${DATADIR}/kupfer", conf.env)
    Logs.pprint("NORMAL",
            "Installing python modules into: %(PYTHONDIR)s" % conf.env)

    opt_build_programs = {
            "rst2man": "Generate and install man page",
        }
    for prog in opt_build_programs:
        try:
            conf.find_program(prog, var=prog.replace("-", "_").upper())
        except conf.errors.ConfigurationError:
            Logs.pprint("YELLOW",
                         "Optional, allows: %s" % opt_build_programs[prog])

    if not Options.options.check_deps:
        return

    python_modules = """
        gi.repository.Gtk
        xdg
        dbus
        """
    for module in python_modules.split():
        conf.check_python_module(module)

    Logs.pprint("NORMAL", "Checking optional dependencies:")

    opt_programs = {
            "dbus-send": "Focus kupfer from the command line",
        }
    opt_pymodules = {
        "gi.repository.Wnck": "Jump to running applications and list windows",
        "gi.repository.Keybinder": "Register global keybindings",
    }

    for prog in opt_programs:
        try:
            conf.find_program(prog, var=prog.replace("-", "_").upper())
        except conf.errors.ConfigurationError:
            Logs.pprint("YELLOW", "Optional, allows: %s" % opt_programs[prog])

    for mod in opt_pymodules:
        try:
            conf.check_python_module(mod)
        except Configure.ConfigurationError:
            Logs.pprint("YELLOW", "module %s is recommended, allows %s" % (
                mod, opt_pymodules[mod]))


def _new_package(bld, name):
    """Add module @name to sources to be installed,
    where the name is the full (relative) path to the package
    """
    obj = bld("py")
    node = bld.path.find_dir(name)
    obj.source = node.ant_glob("*.py")
    obj.install_path = "${PYTHONDIR}/%s" % name

    # Find embedded package datafiles
    pkgnode = bld.path.find_dir(name)

    bld.install_files(obj.install_path, pkgnode.ant_glob("icon-list"))
    bld.install_files(obj.install_path, pkgnode.ant_glob("*.png"))
    bld.install_files(obj.install_path, pkgnode.ant_glob("*.svg"))

def _find_packages_in_directory(bld, name):
    """Go through directory @name and recursively add all
    Python packages with contents to the sources to be installed
    """
    for dirname, dirs, filenames in os.walk(name):
        if "__init__.py" in filenames:
            _new_package(bld, dirname)

def _dict_slice(D, keys):
    return dict((k,D[k]) for k in keys)

def build(bld):
    # always read new version
    bld.env["VERSION"] = VERSION

    # kupfer/
    # kupfer module version info file
    version_subst_file = "kupfer/version_subst.py"
    bld(features="subst",
        source=version_subst_file + ".in",
        target=version_subst_file,
        dict = _dict_slice(bld.env,"VERSION DATADIR PACKAGE LOCALEDIR".split())
        )
    bld.install_files("${PYTHONDIR}/kupfer", "kupfer/version_subst.py")

    bld(
        source="kupfer.py",
        install_path="${PYTHONDIR}"
        )

    # Add all Python packages recursively
    _find_packages_in_directory(bld, "kupfer")

    # bin/
    # Write in some variables in the shell script binaries
    bld(features="subst",
        source = "bin/kupfer.in",
        target = "bin/kupfer",
        dict = _dict_slice(bld.env, "PYTHON PYTHONDIR".split())
        )
    bld.install_files("${BINDIR}", "bin/kupfer", chmod=0o755)

    bld(features="subst",
        source = "bin/kupfer-exec.in",
        target = "bin/kupfer-exec",
        dict = _dict_slice(bld.env, "PYTHON PACKAGE LOCALEDIR".split())
        )
    bld.install_files("${BINDIR}", "bin/kupfer-exec", chmod=0o755)

    # Documentation/
    if bld.env["RST2MAN"]:
        # generate man page from Manpage.rst
        bld(
            source = "Documentation/Manpage.rst",
            target = "kupfer.1",
            rule = '%s ${SRC} > ${TGT}' % bld.env["RST2MAN"],
        )
        bld.add_group()
        # compress and install man page
        manpage = bld(
            source = "kupfer.1",
            target = "kupfer.1.gz",
            rule = 'gzip -9 -c ${SRC} > ${TGT}',
            install_path = "${MANDIR}/man1",
        )
        man_path = Utils.subst_vars(
                os.path.join(manpage.install_path, manpage.target),
                bld.env)
        bld.symlink_as("${MANDIR}/man1/kupfer-exec.1.gz", man_path)

    # Separate subdirectories
    bld.recurse(build_subdirs)

def distclean(bld):
    bld.exec_command("find ./ -name '*.pyc' -delete")

def intlupdate(util):
    print("You should use intltool-update directly.")
    print("You can read about this in Documentation/Manual.rst")
    print("in the localization chapter!")

def test(bld):
    # find all files with doctests
    python = os.getenv("PYTHON", "python")
    paths = os.popen("grep -lR 'doctest.testmod()' kupfer/").read().split()
    os.putenv("PYTHONPATH", ".")
    all_success = True
    verbose = ("-v" in sys.argv)
    for p in paths:
        print(p)
        cmd = [python, p]
        if verbose:
            cmd.append("-v")
        sin, souterr = os.popen4(cmd)
        sin.close()
        res = souterr.read()
        souterr.close()
        print (res or "OK")
        all_success = all_success and bool(res)
    return all_success

def shutdown(bld):
    pass


