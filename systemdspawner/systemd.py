"""
Systemd service utilities.

Contains functions to start, stop & poll systemd services.
Probably not very useful outside this spawner.
"""

import asyncio
import functools
import os
import re
import shlex
import shutil
import subprocess
import warnings

# light validation of environment variable keys
env_pat = re.compile("[A-Za-z_]+")

RUN_ROOT = "/run"


def ensure_environment_directory(environment_file_directory):
    """Ensure directory for environment files exists and is private"""
    # ensure directory exists
    os.makedirs(environment_file_directory, mode=0o700, exist_ok=True)
    # validate permissions
    mode = os.stat(environment_file_directory).st_mode
    if mode & 0o077:
        warnings.warn(
            f"Fixing permissions on environment directory {environment_file_directory}: {oct(mode)}",
            RuntimeWarning,
        )
        os.chmod(environment_file_directory, 0o700)
    else:
        return
    # Check again after supposedly fixing.
    # Some filesystems can have weird issues, preventing this from having desired effect
    mode = os.stat(environment_file_directory).st_mode
    if mode & 0o077:
        warnings.warn(
            f"Bad permissions on environment directory {environment_file_directory}: {oct(mode)}",
            RuntimeWarning,
        )


def make_environment_file(environment_file_directory, unit_name, environment_variables):
    """Make a systemd environment file

    - ensures environment directory exists and is private
    - writes private environment file
    - returns path to created environment file
    """
    ensure_environment_directory(environment_file_directory)
    env_file = os.path.join(environment_file_directory, f"{unit_name}.env")
    env_lines = []
    for key, value in sorted(environment_variables.items()):
        assert env_pat.match(key), f"{key} not a valid environment variable"
        env_lines.append(f"{key}={shlex.quote(value)}")
    env_lines.append("")  # trailing newline
    with open(env_file, mode="w") as f:
        # make the file itself private as well
        os.fchmod(f.fileno(), 0o400)
        f.write("\n".join(env_lines))

    return env_file


async def start_transient_service(
    unit_name,
    cmd,
    args,
    working_dir,
    environment_variables=None,
    properties=None,
    uid=None,
    gid=None,
    slice=None,
):
    """
    Start a systemd transient service using systemd-run with given command-line
    options and systemd unit directives (properties).

    systemd-run ref:             https://www.freedesktop.org/software/systemd/man/systemd-run.html
    systemd unit directives ref: https://www.freedesktop.org/software/systemd/man/systemd.directives.html
    """

    run_cmd = [
        "systemd-run",
        "--unit",
        unit_name,
        "--working-directory",
        working_dir,
    ]
    if uid is not None:
        run_cmd += [f"--uid={uid}"]
    if gid is not None:
        run_cmd += [f"--gid={gid}"]
    if slice:
        run_cmd += [f"--slice={slice}"]

    properties = (properties or {}).copy()

    # Ensure there is a runtime directory where we can put our env file, make
    # runtime directories private by default, and preserve runtime directories
    # across restarts to allow `systemctl restart` to load the env.
    #
    # ref: https://www.freedesktop.org/software/systemd/man/systemd.exec.html#RuntimeDirectory=
    # ref: https://www.freedesktop.org/software/systemd/man/systemd.exec.html#RuntimeDirectoryMode=
    # ref: https://www.freedesktop.org/software/systemd/man/systemd.exec.html#RuntimeDirectoryPreserve=
    #
    properties.setdefault("RuntimeDirectory", unit_name)
    properties.setdefault("RuntimeDirectoryMode", "700")
    properties.setdefault("RuntimeDirectoryPreserve", "restart")

    # Ensure that out of memory killing of a process run inside the user server
    # (systemd unit), such as a Jupyter kernel, doesn't result in stopping or
    # killing the user server.
    #
    # ref: https://www.freedesktop.org/software/systemd/man/systemd.service.html#OOMPolicy=
    #
    properties.setdefault("OOMPolicy", "continue")

    # Pass configured properties via systemd-run's --property flag
    for key, value in properties.items():
        if isinstance(value, list):
            # The properties dictionary is allowed to have a list of values for
            # each of its keys as a way of allowing the same key to be passed
            # multiple times.
            run_cmd += [f"--property={key}={v}" for v in value]
        else:
            # A string!
            run_cmd.append(f"--property={key}={value}")

    # Create and reference an environment variable file in the first
    # RuntimeDirectory entry, which is a whitespace-separated list of directory
    # names.
    #
    # ref: https://www.freedesktop.org/software/systemd/man/systemd.exec.html#EnvironmentFile=
    #
    if environment_variables:
        runtime_dir = os.path.join(RUN_ROOT, properties["RuntimeDirectory"].split()[0])
        environment_file = make_environment_file(
            runtime_dir, unit_name, environment_variables
        )
        run_cmd.append(f"--property=EnvironmentFile={environment_file}")

    # make sure cmd[0] is absolute, taking $PATH into account.
    # systemd-run does not use the unit's $PATH environment
    # to resolve relative paths.
    if not os.path.isabs(cmd[0]):
        if environment_variables and "PATH" in environment_variables:
            # if unit specifies a $PATH, use it
            path = environment_variables["PATH"]
        else:
            # search current process $PATH by default.
            # this is the default behavior of shutil.which(path=None)
            # but we still need the value for the error message
            path = os.getenv("PATH", os.defpath)
        exe = cmd[0]
        abs_exe = shutil.which(exe, path=path)
        if not abs_exe:
            raise FileNotFoundError(f"{exe} not found on {path}")
        cmd[0] = abs_exe

    # Append typical Spawner "cmd" and "args" on how to start the user server
    run_cmd += cmd + args

    proc = await asyncio.create_subprocess_exec(*run_cmd)

    return await proc.wait()


async def service_running(unit_name):
    """
    Return true if service with given name is running (active).
    """
    proc = await asyncio.create_subprocess_exec(
        "systemctl",
        "is-active",
        unit_name,
        # hide stdout, but don't capture stderr at all
        stdout=asyncio.subprocess.DEVNULL,
    )
    ret = await proc.wait()

    return ret == 0


async def service_failed(unit_name):
    """
    Return true if service with given name is in a failed state.
    """
    proc = await asyncio.create_subprocess_exec(
        "systemctl",
        "is-failed",
        unit_name,
        # hide stdout, but don't capture stderr at all
        stdout=asyncio.subprocess.DEVNULL,
    )
    ret = await proc.wait()

    return ret == 0


async def stop_service(unit_name):
    """
    Stop service with given name.

    Throws CalledProcessError if stopping fails
    """
    proc = await asyncio.create_subprocess_exec("systemctl", "stop", unit_name)
    await proc.wait()


async def reset_service(unit_name):
    """
    Reset service with given name.

    Throws CalledProcessError if resetting fails
    """
    proc = await asyncio.create_subprocess_exec("systemctl", "reset-failed", unit_name)
    await proc.wait()


@functools.lru_cache
def get_systemd_version():
    """
    Returns systemd's major version, or None if failing to do so.
    """
    try:
        version_response = subprocess.check_output(["systemctl", "--version"])
    except Exception as e:
        warnings.warn(
            f"Failed to run `systemctl --version` to get systemd version: {e}",
            RuntimeWarning,
            stacklevel=2,
        )

    try:
        # Example response from Ubuntu 22.04:
        #
        # systemd 249 (249.11-0ubuntu3.9)
        # +PAM +AUDIT +SELINUX +APPARMOR +IMA +SMACK +SECCOMP +GCRYPT +GNUTLS +OPENSSL +ACL +BLKID +CURL +ELFUTILS +FIDO2 +IDN2 -IDN +IPTC +KMOD +LIBCRYPTSETUP +LIBFDISK +PCRE2 -PWQUALITY -P11KIT -QRENCODE +BZIP2 +LZ4 +XZ +ZLIB +ZSTD -XKBCOMMON +UTMP +SYSVINIT default-hierarchy=unified
        #
        version = int(float(version_response.split()[1]))
        return version
    except Exception as e:
        warnings.warn(
            f"Failed to parse systemd version from `systemctl --version`: {e}. output={version_response}",
            RuntimeWarning,
            stacklevel=2,
        )
        return None
