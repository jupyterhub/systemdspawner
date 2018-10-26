import os
import pwd
import subprocess
from traitlets import Bool, Unicode, List, Dict
import asyncio
import shlex

from systemdspawner import systemd

from jupyterhub.spawner import Spawner
from jupyterhub.utils import random_port


class SystemdNonTransientSpawner(Spawner):
    unit_template = Unicode(
        'jupyter-singleuser@{USERNAME}.service',
        help="""
        Name of the systemd service template including templated part.

        {USERNAME} and {USERID} are expanded.
        """
    ).tag(config=True)

    envfile_template = Unicode(
        '/srv/jupyterhub/envs/{USERNAME}.env',
        help="""
        Path of the environment file for a single user server.

        {USERNAME} and {USERID} are expanded.
        """
    )

    use_sudo = Bool(
        False,
        help="""
        Use sudo to start and stop systemd services.

        If set to False, sudo will not be used and you will have to a policykit
        rule to allow the Jupyterhub user to start and stop the singleuser server
        services. This requires policykitversion larger than 105, which are not
        available in Debian or Ubuntu and its derivatives.
        """
    ).tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # All traitlets configurables are configured by now
        self.unit_name = self._expand_user_vars(self.unit_template)
        self.envfilepath = self._expand_user_vars(self.envfile_template)

        self.log.debug('user:%s Initialized spawner with unit %s', self.user.name, self.unit_name)

    def _expand_user_vars(self, string):
        """
        Expand user related variables in a given string

        Currently expands:
          {USERNAME} -> Name of the user
          {USERID} -> UserID
        """
        return string.format(
            USERNAME=self.user.name,
            USERID=self.user.id
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
        Load state from storage required to reinstate this user's server

        This runs after __init__, so we can override it with saved unit name
        if needed. This is useful primarily when you change the unit name template
        between restarts.

        JupyterHub before 0.7 also assumed your notebook was dead if it
        saved no state, so this helps with that too!
        """
        if 'unit_name' in state:
            self.unit_name = state['unit_name']

        if self.unit_name != self._expand_user_vars(self.unit_template):
            self.log.debug("Trying to reinstate an outdated unit name that does not match unit_template!")

    def _set_envfile_acl(self):
        acl = self._expand_user_vars("u:{USERNAME}:rw")
        self.log.debug("Setting ACL %s on %s", acl, self.envfilepath)
        subprocess.run(['setfacl', '-m', acl, self.envfilepath], check=True)

    async def start(self):
        self.port = random_port()
        self.log.debug('user:%s Using port %s to start spawning user server', self.user.name, self.port)

        # If there's a unit with this name running already. This means a bug in
        # JupyterHub, a remnant from a previous install or a failed service start
        # from earlier. Regardless, we kill it and start ours in its place.
        # FIXME: Carefully look at this when doing a security sweep.
        if await systemd.service_running(self.unit_name):
            await systemd.stop_service(self.unit_name, self.use_sudo)
            self.log.info('user:%s Unit %s already exists but not known to JupyterHub. Killing', self.user.name, self.unit_name)
            if await systemd.service_running(self.unit_name):
                self.log.error('user:%s Could not stop already existing unit %s', self.user.name, self.unit_name)
                raise Exception('Could not stop already existing unit {}'.format(self.unit_name))

        # If there's a unit with this name already but sitting in a failed state.
        # Does a reset of the state before trying to start it up again.
        if await systemd.service_failed(self.unit_name):
            self.log.info('user:%s Unit %s in a failed state. Resetting state.', self.user.name, self.unit_name)
            await systemd.reset_service(self.unit_name, self.use_sudo)

        env = self.get_env()
        env['USERINSTANCEARGS'] = ' '.join([shlex.quote(self._expand_user_vars(a)) for a in self.get_args()])

        self.log.debug('writing user server environment file %s', self.envfilepath)
        with open(self.envfilepath, 'w') as envfile:
            os.chmod(self.envfilepath, 0o600)
            envfile.writelines(
                '\n'.join('{k}={v}'.format(k=k, v=v) for k, v in env.items())
            )
        self._set_envfile_acl()

        if self.use_sudo:
            sudo_cmd = 'sudo '
        else:
            sudo_cmd = ''

        self.log.debug('running %ssystemctl start %s', sudo_cmd, self.unit_name)
        ret = await systemd.start_service(self.unit_name, self.use_sudo)
        self.log.debug('%ssystemctl start %s returned with %s', sudo_cmd, self.unit_name, ret)

        for i in range(self.start_timeout):
            is_up = await self.poll()
            if is_up is None:
                self.log.debug('systemctl is-active %s: %s', self.unit_name, bool(is_up))
                self.log.debug('returning now, the rest is out of my hands')
                return (self.ip or '127.0.0.1', self.port)
            await asyncio.sleep(1)

        self.log.debug('systemctl is-active %s: %s', self.unit_name, bool(is_up))
        return None

    async def stop(self, now=False):
        await systemd.stop_service(self.unit_name, self.use_sudo)
        os.remove(self.envfilepath)

    async def poll(self):
        if await systemd.service_running(self.unit_name):
            return None
        return 1
