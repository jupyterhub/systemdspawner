import os
import pwd
import time
import subprocess
import shlex
from traitlets import Bool, Int, Unicode, List
from tornado import gen

from jupyterhub.spawner import Spawner
from jupyterhub.utils import random_port


class SystemdSpawner(Spawner):
    user_workingdir = Unicode(
        '/home/{USERNAME}', help='Path to start each notebook user on. {USERNAME} and {USERID} are expanded. {USERHOME} is expanded as user home directory as declared on the system.').tag(config=True)

    default_shell = Unicode(
        os.environ.get('SHELL', '/bin/bash'),
        help='Default shell for users on the notebook terminal'
    ).tag(config=True)

    extra_paths = List(
        [],
        help='Extra paths to prepend to the $PATH environment variable. {USERHOME}, {USERNAME} and {USERID} are expanded',
    ).tag(config=True)

    unit_name_template = Unicode(
        'jupyter-{USERNAME}-singleuser',
        help='Template to use to make the systemd service names. {USERHOME}, {USERNAME} and {USERID} are expanded}'
    ).tag(config=True)

    # FIXME: Do not allow enabling this for systemd versions < 227,
    # since that is when it was introduced.
    isolate_tmp = Bool(
        False,
        help='Give each notebook user their own /tmp, isolated from the system & each other'
    ).tag(config=True)

    isolate_devices = Bool(
        False,
        help='Give each notebook user their own /dev, with a very limited set of devices mounted'
    ).tag(config=True)

    disable_user_sudo = Bool(
        False,
        help='Set to true to disallow becoming root (or any other user) via sudo or other means from inside the notebook',
    ).tag(config=True)

    readonly_paths = List(
        None,
        allow_none=True,
        help='List of paths that should be marked readonly from the user notebook. Subpaths can be overriden by setting readwrite_paths',
    ).tag(config=True)

    readwrite_paths = List(
        None,
        allow_none=True,
        help='List of paths that should be marked read-write from the user notebook. Usually used to make a subpath of a readonly path writeable',
    ).tag(config=True)

    unit_extra_properties = List(
        None,
        allow_none=True,
        help="""
        List of extra properties for systemd-run --property=[...].
        Used to add arbitrary properties for spawned Jupyter units.
        Read `man systemd-run` for details on per-unit properties.
        """
    ).tag(config=True)

    use_sudo = Bool(
        False,
        help="""
        Use sudo to run systemd-run / systemctl commands.

        Useful if you want to run jupyterhub as a non-root user and have set up sudo rules to allow
        it to call systemd-run / systemctl commands
        """
    ).tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # All traitlets configurables are configured by now
        self.systemctl_cmd = ['/bin/systemctl']
        self.systemd_run_cmd = ['/usr/bin/systemd-run']
        if self.use_sudo:
            self.systemctl_cmd.insert(0, '/usr/bin/sudo')
            self.systemd_run_cmd.insert(0, '/usr/bin/sudo')

        self.unit_name = self._expand_user_vars(self.unit_name_template)

        self.log.debug('user:%s Initialized spawner with unit %s', self.user.name, self.unit_name)


    def _expand_user_vars(self, string):
        """
        Expand user related variables in a given string

        Currently expands:
          {USERHOME} -> User home directory
          {USERNAME} -> Name of the user
          {USERID} -> UserID
        """
        import os.path
        return string.format(
            USERNAME=self.user.name,
            USERID=self.user.id,
            USERHOME=os.path.expanduser('~{}'.format(self.user.name))
        )

    def get_state(self):
        """
        Save state required to reconstruct spawner from scratch

        We save the unit name, just in case the unit template was changed
        between a restart. We do not want to lost the previously launched
        events.

        JupyterHub before 0.7 also assumed your notebook was dead if it
        saved no state, so this helps with that too!
        """
        state = super().get_state()
        state['unit_name'] = self.unit_name
        return state

    def load_state(self, state):
        """
        Load state from storage required to reinstate this user's pod

        This runs after __init__, so we can override it with saved unit name
        if needed. This is useful primarily when you change the unit name template
        between restarts.

        JupyterHub before 0.7 also assumed your notebook was dead if it
        saved no state, so this helps with that too!
        """
        if 'unit_name' in state:
            self.unit_name = state['unit_name']

    @gen.coroutine
    def start(self):
        self.port = random_port()
        self.log.debug('user:%s Using port %s to start spawning user server', self.user.name, self.port)

        # if a previous attempt to start the service for this user was made and failed,
        # systemd keeps the service around in 'failed' state. This will prevent future
        # services with the same name from being started. While this behavior makes sense
        # (since if it fails & is deleted immediately, we will lose state info), in our
        # case it is ok to reset it and move on when trying to start again.
        try:
            if subprocess.check_output(self.systemctl_cmd + [
                'is-failed',
                self.unit_name
            ]).decode('utf-8').strip() == 'failed':
                subprocess.check_output(self.systemctl_cmd + [
                    'reset-failed',
                    self.unit_name
                ])
                self.log.info('user:%s Unit %s in failed state, resetting', self.user.name, self.unit_name)
        except subprocess.CalledProcessError as e:
            # This is returned when the unit is *not* in failed state. bah!
            pass
        env = self.get_env()

        cmd = self.systemd_run_cmd[:]

        cmd.extend(['--unit', self.unit_name])
        try:
            pwnam = pwd.getpwnam(self.user.name)
        except KeyError:
            self.log.exception('No user named %s found in the system' % self.user.name)
            raise
        cmd.extend(['--uid', str(pwnam.pw_uid), '--gid', str(pwnam.pw_gid)])

        if self.isolate_tmp:
            cmd.extend(['--property=PrivateTmp=yes'])

        if self.isolate_devices:
            cmd.extend(['--property=PrivateDevices=yes'])

        if self.extra_paths:
            env['PATH'] = '{extrapath}:{curpath}'.format(
                curpath=env['PATH'],
                extrapath=':'.join(
                    [self._expand_user_vars(p) for p in self.extra_paths]
                )
            )

        for key, value in env.items():
            cmd.append('--setenv={key}={value}'.format(key=key, value=value))

        cmd.append('--setenv=SHELL={shell}'.format(shell=self.default_shell))

        if self.mem_limit is not None:
            # FIXME: Detect & use proper properties for v1 vs v2 cgroups
            cmd.extend([
                '--property=MemoryAccounting=yes',
                '--property=MemoryLimit={mem}'.format(mem=self.mem_limit),
            ])

        if self.cpu_limit is not None:
            # FIXME: Detect & use proper properties for v1 vs v2 cgroups
            # FIXME: Make sure that the kernel supports CONFIG_CFS_BANDWIDTH
            #        otherwise this doesn't have any effect.
            cmd.extend([
                '--property=CPUAccounting=yes',
                '--property=CPUQuota={quota}%'.format(quota=int(self.cpu_limit * 100))
            ])

        if self.disable_user_sudo:
            cmd.append('--property=NoNewPrivileges=yes')

        if self.readonly_paths is not None:
            cmd.extend([
                self._expand_user_vars('--property=ReadOnlyDirectories=-{path}'.format(path=path))
                for path in self.readonly_paths
            ])

        if self.readwrite_paths is not None:
            cmd.extend([
                self._expand_user_vars('--property=ReadWriteDirectories={path}'.format(path=path))
                for path in self.readwrite_paths
            ])

        if self.unit_extra_properties is not None:
            cmd.extend([
                self._expand_user_vars('--property={prop}'.format(prop=prop))
                for prop in self.unit_extra_properties
            ])

        # We unfortunately have to resort to doing cd with bash, since WorkingDirectory property
        # of systemd units can't be set for transient units via systemd-run until systemd v227.
        # Centos 7 has systemd 219, and will probably never upgrade - so we need to support them.
        bash_cmd = [
            '/bin/bash',
            '-c',
            "cd {wd} && exec {cmd} {args}".format(
                wd=shlex.quote(self._expand_user_vars(self.user_workingdir)),
                cmd=' '.join([shlex.quote(self._expand_user_vars(c)) for c in self.cmd]),
                args=' '.join([shlex.quote(a) for a in self.get_args()])
            )
        ]
        cmd.extend(bash_cmd)

        self.log.debug('user:%s Running systemd-run with: %s', self.user.name, ' '.join(cmd))
        subprocess.check_output(cmd)

        for i in range(self.start_timeout):
            is_up = yield self.poll()
            if is_up is None:
                return (self.ip or '127.0.0.1', self.port)
            yield gen.sleep(1)

        return None

    @gen.coroutine
    def stop(self, now=False):
        subprocess.check_output(self.systemctl_cmd + [
            'stop',
            self.unit_name
        ])

    @gen.coroutine
    def poll(self):
        try:
            if subprocess.check_call(self.systemctl_cmd + [
                'is-active',
                self.unit_name
            ], stdout=open('/dev/null', 'w'), stderr=open('/dev/null', 'w')) == 0:
                self.log.debug('user:%s unit %s is active', self.user.name, self.unit_name)
                return None
        except subprocess.CalledProcessError as e:
            self.log.debug('user:%s unit %s is not active', self.user.name, self.unit_name)
            return e.returncode
