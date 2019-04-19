"""
Systemd service utilities.

Contains functions to start, stop & poll systemd services.
Probably not very useful outside this spawner.
"""
import asyncio
import shlex


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
    Start a systemd transient service with given paramters
    """

    run_cmd = [
        'systemd-run',
        '--unit', unit_name,
    ]

    if properties:
        for key, value in properties.items():
            if isinstance(value, list):
                run_cmd += ['--property={}={}'.format(key, v) for v in value]
            else:
                # A string!
                run_cmd.append('--property={}={}'.format(key, value))

    if environment_variables:
        run_cmd += [
            '--setenv={}={}'.format(key, value)
            for key, value in environment_variables.items()
        ]

    # Explicitly check if uid / gid are not None, since 0 is valid value for both
    if uid is not None:
        run_cmd += ['--uid', str(uid)]

    if gid is not None:
        run_cmd += ['--gid', str(gid)]

    if slice is not None:
        run_cmd += ['--slice={}'.format(slice)]
    
    run_cmd.append('--property=WorkingDirectory={}'.format(shlex.quote(working_dir)))
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
