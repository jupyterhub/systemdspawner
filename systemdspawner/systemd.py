"""
Systemd service utilities.

Contains functions to start, stop & poll systemd services.
Probably not very useful outside this spawner.
"""

import asyncio
import os
import re
import shlex
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
    Start a systemd transient service with given parameters
    """

    run_cmd = [
        'systemd-run',
        '--unit', unit_name,
    ]

    if properties is None:
        properties = {}
    else:
        properties = properties.copy()

    # ensure there is a runtime directory where we can put our env file
    # If already set, can be space-separated list of paths
    runtime_directories = properties.setdefault("RuntimeDirectory", unit_name).split()

    # runtime directories are always resolved relative to `/run`
    # grab the first item, if more than one
    runtime_dir = os.path.join(RUN_ROOT, runtime_directories[0])
    # make runtime directories private by default
    properties.setdefault("RuntimeDirectoryMode", "700")
    # preserve runtime directories across restarts
    # allows `systemctl restart` to load the env
    properties.setdefault("RuntimeDirectoryPreserve", "restart")

    if properties:
        for key, value in properties.items():
            if isinstance(value, list):
                run_cmd += ['--property={}={}'.format(key, v) for v in value]
            else:
                # A string!
                run_cmd.append('--property={}={}'.format(key, value))

    if environment_variables:
        environment_file = make_environment_file(
            runtime_dir, unit_name, environment_variables
        )
        run_cmd.append(f"--property=EnvironmentFile={environment_file}")

    # Explicitly check if uid / gid are not None, since 0 is valid value for both
    if uid is not None:
        run_cmd += ['--uid', str(uid)]

    if gid is not None:
        run_cmd += ['--gid', str(gid)]

    if slice is not None:
        run_cmd += ['--slice={}'.format(slice)]

    # We unfortunately have to resort to doing cd with bash, since WorkingDirectory property
    # of systemd units can't be set for transient units via systemd-run until systemd v227.
    # Centos 7 has systemd 219, and will probably never upgrade - so we need to support them.
    run_cmd += [
        '/bin/bash',
        '-c',
        "cd {wd} && exec {cmd} {args}".format(
            wd=shlex.quote(working_dir),
            cmd=' '.join([shlex.quote(c) for c in cmd]),
            args=' '.join([shlex.quote(a) for a in args])
        )
    ]

    proc = await asyncio.create_subprocess_exec(*run_cmd)

    return await proc.wait()


async def service_running(unit_name):
    """
    Return true if service with given name is running (active).
    """
    proc = await asyncio.create_subprocess_exec(
        'systemctl',
        'is-active',
        unit_name,
        # hide stdout, but don't capture stderr at all
        stdout=asyncio.subprocess.DEVNULL
    )
    ret = await proc.wait()

    return ret == 0


async def service_failed(unit_name):
    """
    Return true if service with given name is in a failed state.
    """
    proc = await asyncio.create_subprocess_exec(
        'systemctl',
        'is-failed',
        unit_name,
        # hide stdout, but don't capture stderr at all
        stdout=asyncio.subprocess.DEVNULL
    )
    ret = await proc.wait()

    return ret == 0


async def stop_service(unit_name):
    """
    Stop service with given name.

    Throws CalledProcessError if stopping fails
    """
    proc = await asyncio.create_subprocess_exec(
        'systemctl',
        'stop',
        unit_name
    )
    await proc.wait()


async def reset_service(unit_name):
    """
    Reset service with given name.

    Throws CalledProcessError if resetting fails
    """
    proc = await asyncio.create_subprocess_exec(
        'systemctl',
        'reset-failed',
        unit_name
    )
    await proc.wait()
