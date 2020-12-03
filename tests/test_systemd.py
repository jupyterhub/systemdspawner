"""
Test systemd wrapper utilities.

Must run as root.
"""
import tempfile
from systemdspawner import systemd
import pytest
import asyncio
import os
import time


@pytest.mark.asyncio
async def test_simple_start():
    unit_name = 'systemdspawner-unittest-' + str(time.time())
    await systemd.start_transient_service(
        unit_name,
        ['sleep'],
        ['2000'],
        working_dir='/'
    )

    assert await systemd.service_running(unit_name)

    await systemd.stop_service(unit_name)

    assert not await systemd.service_running(unit_name)


@pytest.mark.asyncio
async def test_service_failed_reset():
    """
    Test service_failed and reset_service
    """
    unit_name = 'systemdspawner-unittest-' + str(time.time())
    # Running a service with an invalid UID makes it enter a failed state
    await systemd.start_transient_service(
        unit_name,
        ['sleep'],
        ['2000'],
        working_dir='/systemdspawner-unittest-does-not-exist'
    )

    await asyncio.sleep(0.1)

    assert await systemd.service_failed(unit_name)

    await systemd.reset_service(unit_name)

    assert not await systemd.service_failed(unit_name)


@pytest.mark.asyncio
async def test_service_running_fail():
    """
    Test service_running failing when there's no service.
    """
    unit_name = 'systemdspawner-unittest-' + str(time.time())

    assert not await systemd.service_running(unit_name)


@pytest.mark.asyncio
async def test_env_setting():
    unit_name = 'systemdspawner-unittest-' + str(time.time())
    with tempfile.TemporaryDirectory() as d:
        os.chmod(d, 0o777)
        await systemd.start_transient_service(
            unit_name,
            ["/bin/bash"],
            ["-c", "pwd; ls -la {0}; env > ./env; sleep 3".format(d)],
            working_dir=d,
            environment_variables={
                "TESTING_SYSTEMD_ENV_1": "TEST 1",
                "TESTING_SYSTEMD_ENV_2": "TEST 2",
            },
            # set user to ensure we are testing permission issues
            properties={
                "User": "65534",
            },
        )
        env_dir = os.path.join(systemd.RUN_ROOT, unit_name)
        assert os.path.isdir(env_dir)
        assert (os.stat(env_dir).st_mode & 0o777) == 0o700

        # Wait a tiny bit for the systemd unit to complete running
        await asyncio.sleep(0.1)
        assert await systemd.service_running(unit_name)

        env_file = os.path.join(env_dir, f"{unit_name}.env")
        assert os.path.exists(env_file)
        assert (os.stat(env_file).st_mode & 0o777) == 0o400
        # verify that the env had the desired effect
        with open(os.path.join(d, 'env')) as f:
            text = f.read()
            assert "TESTING_SYSTEMD_ENV_1=TEST 1" in text
            assert "TESTING_SYSTEMD_ENV_2=TEST 2" in text

        await systemd.stop_service(unit_name)
        assert not await systemd.service_running(unit_name)
        # systemd cleans up env file
        assert not os.path.exists(env_file)


@pytest.mark.asyncio
async def test_workdir():
    unit_name = 'systemdspawner-unittest-' + str(time.time())
    _, env_filename = tempfile.mkstemp()
    with tempfile.TemporaryDirectory() as d:
        await systemd.start_transient_service(
            unit_name,
            ['/bin/bash'],
            ['-c', 'pwd > {}/pwd'.format(d)],
            working_dir=d,
        )

        # Wait a tiny bit for the systemd unit to complete running
        await asyncio.sleep(0.1)
 
        with open(os.path.join(d, 'pwd')) as f:
            text = f.read().strip()
            assert text == d


@pytest.mark.asyncio
async def test_slice():
    unit_name = 'systemdspawner-unittest-' + str(time.time())
    _, env_filename = tempfile.mkstemp()
    with tempfile.TemporaryDirectory() as d:
        await systemd.start_transient_service(
            unit_name,
            ['/bin/bash'],
            ['-c', 'pwd > {}/pwd; sleep 10;'.format(d)],
            working_dir=d,
            slice='user.slice',
        )

        # Wait a tiny bit for the systemd unit to complete running
        await asyncio.sleep(0.1)

        proc = await asyncio.create_subprocess_exec(
            *['systemctl', 'status', unit_name],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

        stdout, stderr = await proc.communicate()
        assert b'user.slice' in stdout


@pytest.mark.asyncio
async def test_properties_string():
    """
    Test that setting string properties works

    - Make a temporary directory
    - Bind mount temporary directory to /bind-test
    - Start process in /bind-test, write to current-directory/pwd the working directory
    - Read it from the *temporary* directory, verify it is /bind-test

    This validates the Bind Mount is working, and hence properties are working.
    """
    unit_name = 'systemdspawner-unittest-' + str(time.time())
    _, env_filename = tempfile.mkstemp()
    with tempfile.TemporaryDirectory() as d:
        await systemd.start_transient_service(
            unit_name,
            ['/bin/bash'],
            ['-c', 'pwd > pwd'.format(d)],
            working_dir='/bind-test',
            properties={
                'BindPaths': '{}:/bind-test'.format(d)
            }
        )

        # Wait a tiny bit for the systemd unit to complete running
        await asyncio.sleep(0.1)
        with open(os.path.join(d, 'pwd')) as f:
            text = f.read().strip()
            assert text == '/bind-test'


@pytest.mark.asyncio
async def test_properties_list():
    """
    Test setting multiple values for a property

    - Make a temporary directory
    - Before starting process, run two mkdir commands to create a nested
      directory. These commands must be run in order by systemd, otherewise
      they will fail. This validates that ordering behavior is preserved.
    - Start a process in temporary directory
    - Write current directory to nested directory created in ExecPreStart

    This validates multiple ordered ExcePreStart calls are working, and hence
    properties with lists as values are working.
    """
    unit_name = 'systemdspawner-unittest-' + str(time.time())
    _, env_filename = tempfile.mkstemp()
    with tempfile.TemporaryDirectory() as d:
        await systemd.start_transient_service(
            unit_name,
            ['/bin/bash'],
            ['-c', 'pwd > test-1/test-2/pwd'],
            working_dir=d,
            properties={
                "ExecStartPre": [
                    f"/bin/mkdir -p {d}/test-1/test-2",
                ],
            },
        )

        # Wait a tiny bit for the systemd unit to complete running
        await asyncio.sleep(0.1)
        with open(os.path.join(d, 'test-1', 'test-2', 'pwd')) as f:
            text = f.read().strip()
            assert text == d


@pytest.mark.asyncio
async def test_uid_gid():
    """
    Test setting uid and gid

    - Make a temporary directory
    - Run service as uid 65534 (nobody) and gid 0 (root)
    - Verify the output of the 'id' command

    This validates that setting uid sets uid, gid sets the gid
    """
    unit_name = 'systemdspawner-unittest-' + str(time.time())
    _, env_filename = tempfile.mkstemp()
    with tempfile.TemporaryDirectory() as d:
        os.chmod(d, 0o777)
        await systemd.start_transient_service(
            unit_name,
            ['/bin/bash'],
            ['-c', 'id > id'],
            working_dir=d,
            uid=65534,
            gid=0
        )

        # Wait a tiny bit for the systemd unit to complete running
        await asyncio.sleep(0.2)
        with open(os.path.join(d, 'id')) as f:
            text = f.read().strip()
            assert text == 'uid=65534(nobody) gid=0(root) groups=0(root)'
