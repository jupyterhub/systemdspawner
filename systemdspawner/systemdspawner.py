import pwd
import time
import subprocess
from traitlets import Bool, Int
from tornado import gen

from jupyterhub.spawner import Spawner
from jupyterhub.utils import random_port


class SystemdSpawner(Spawner):
    mem_limit = Int(
        0,
        help='Memory limit for each user. Set to 0 (default) for no limits'
    ).tag(config=True)

    run_as_system_users = Bool(
        True,
        help='Run each service with the uid of the user it is authenticated as'
    ).tag(config=True)

    isolate_tmp = Bool(
        True,
        help='Give each notebook user their own /tmp, isolated from the system & each other'
    )

    def load_state(self, state):
        super().load_state(state)
        if 'unit_name' in state:
            self.unit_name = state['unit_name']

    def get_state(self):
        state = super().get_state()
        state['unit_name'] = self.unit_name
        return state

    @gen.coroutine
    def start(self):
        self.port = random_port()
        self.unit_name = 'jupyter-{id}-singleuser'.format(id=self.user.id)

        # if a previous attempt to start the service for this user was made and failed,
        # systemd keeps the service around in 'failed' state. This will prevent future
        # services with the same name from being started. While this behavior makes sense
        # (since if it fails & is deleted immediately, we will lose state info), in our
        # case it is ok to reset it and move on when trying to start again.
        try:
            if subprocess.check_output([
                '/bin/systemctl',
                'is-failed',
                self.unit_name
            ]).decode('utf-8').strip() == 'failed':
                subprocess.check_output([
                    '/bin/systemctl',
                    'reset-failed',
                    self.unit_name
                ])
                self.log.info('Found unit {unit} in failed state, reset state to inactive'.format(
                    unit=self.unit_name)
                )
        except subprocess.CalledProcessError as e:
            # This is returned when the unit is *not* in failed state. bah!
            pass
        env = self.get_env()

        cmd = ['/usr/bin/systemd-run']

        cmd.extend(['--unit', self.unit_name])
        if self.run_as_system_users:
            try:
                pwnam = pwd.getpwnam(self.user.name)
            except KeyError:
                self.log.exception('No user named %s found in the system' % self.user.name)
                raise
            cmd.extend(['--uid', str(pwnam.pw_uid), '--gid', str(pwnam.pw_gid)])

        if self.isolate_tmp:
            cmd.extend(['--property=PrivateTmp=yes'])

        for key, value in env.items():
            cmd.append('--setenv={key}={value}'.format(key=key, value=value))

        if self.mem_limit != 0:
            # FIXME: Detect & use proper properties for v1 vs v2 cgroups
            cmd.extend([
                '--property=MemoryAccounting=yes',
                '--property=MemoryLimit={mem}M'.format(mem=self.mem_limit),
            ])

        cmd.extend(self.cmd)
        cmd.extend(self.get_args())

        self.proc = subprocess.Popen(cmd, start_new_session=True)

        for i in range(self.start_timeout):
            is_up = yield self.poll()
            if is_up is None:
                return (self.ip or '127.0.0.1', self.port)
            time.sleep(1)

        return None

    @gen.coroutine
    def stop(self):
        subprocess.check_output([
            '/bin/systemctl',
            'stop',
            self.unit_name
        ])

    @gen.coroutine
    def poll(self):
        if hasattr(self, 'unit_name'):
            try:
                if subprocess.check_output([
                    '/bin/systemctl',
                    'is-active',
                    self.unit_name
                ]).decode('utf-8').strip() == 'active':
                    return None
            except subprocess.CalledProcessError as e:
                return e.returncode
        return 0
