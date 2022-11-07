import asyncio
import os
import shlex
import shutil
import subprocess
from io import StringIO
from pathlib import Path

from jupyterhub.spawner import Spawner
from jupyterhub.utils import random_port
from traitlets import Bool, Dict, List, Unicode

from systemdspawner import systemd


class StaticSystemdSpawnerError(Exception):
    def __init__(self, msg):
        self.msg = msg
        self.jupyterhub_message = msg
        self.jupyterhub_html_message = f"<p>{msg}</p>"


class StaticSystemdSpawner(Spawner):
    default_server_unit_name_template = Unicode(
        "jupyterhub-singleuser-{USERNAME}.service",
        help="""
        Template to use to make the systemd service name of the default
        singleuser server.

        {USERNAME} and {USERID} are expanded.
        """,
    ).tag(config=True)
    named_server_unit_name_template = Unicode(
        "jupyterhub-singleuser-{USERNAME}@.service",
        help="""
        Template to use to make the systemd service names for named singleuser
        servers. Only used when named servers are enabled.

        {USERNAME} and {USERID} are expanded.
        """,
    ).tag(config=True)
    unit_generator = Unicode(
        "",
        help="""
        Template unit to generate singleuser server units.

        If you want missing singleuser server units generated, set this to the
        name of template unit (e.g. jupyterhub-unitgenerator@.service), that
        you must install seperately that does this.

        Leave empty to not generate missing singleuser server units.
        """,
    ).tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # All traitlets configurables are configured by now
        if self.name:
            # named server
            self.escaped_name = systemd.escape_name(self.name)
            self.unit_name = systemd.fill_template_name(
                self._expand_user_vars(self.named_server_unit_name_template),
                self.name
            )
        else:
            # default server
            self.escaped_name = ""
            self.unit_name = self._expand_user_vars(self.default_server_unit_name_template)
        self.unit_secrets_path = None

        self.log.info(
            "user:%s Initialized spawner with unit %s", self.user.name, self.unit_name
        )

    def _expand_user_vars(self, string):
        """
        Expand user related variables in a given string

        Currently expands:
          {USERNAME} -> Name of the user
          {USERID} -> UserID
          {SERVERNAME} -> Name of the named server
        """
        return string.format(
            USERNAME=self.user.name,
            USERID=self.user.id,
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
        state["unit_name"] = self.unit_name
        state["escaped_name"] = self.escaped_name
        state["unit_secrets_path"] = os.fspath(self.unit_secrets_path)
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
        if "unit_name" in state:
            self.unit_name = state["unit_name"]
        if "escaped_name" in state:
            self.escaped_name = state["escaped_name"]
        if "unit_secrets_path" in state:
            self.unit_secrets_path = Path(state["unit_secrets_path"])

    def _ensure_spawnerconf_directory(self):
        """
        Ensure that the directory we write environment files to exists.
        """
        state_dir = os.getenv("STATE_DIRECTORY")
        if not state_dir:
            raise StaticSystemdSpawnerError("JupyterHub service was configured without StateDirectory=")
        state_dir = state_dir.split(":")[0]
        spawnerconf_dir = Path(state_dir) / "spawnerconf"
        spawnerconf_dir.mkdir(mode=0o700, exist_ok=True)
        return spawnerconf_dir

    def _ensure_user_spawnerconf_directory(self):
        """
        Ensure that the per user directory for spawner configuration exists.

        For the default server this directory will be

            $STATEDIRECTORY/spawnerconf/<username>/default

        and for named servers

            $STATEDIRECTORY/spawnerconf/<username>/named/<escaped servername>
        """
        spawnerconf_dir = self._ensure_spawnerconf_directory()
        userconf_dir = spawnerconf_dir / self.user.name
        userconf_dir.mkdir(mode=0o700, exist_ok=True)
        if self.name:
            userconf_dir = userconf_dir / "named" / self.escaped_name
        else:
            userconf_dir = userconf_dir / "default"
        userconf_dir.mkdir(mode=0o700, exist_ok=True, parents=True)
        return userconf_dir

    def _write_unit_secrets(self):
        """
        Write out secrets for the unit to be started to spawnerconf directory.

        This directory will later be picked up by LoadCredential= and create one
        file in the credential directory for each file in the spawnerconf
        directory.
        """
        # TODO: add systemd.encrypt_creds and use systemd-creds
        # TODO: make the singleuser instance understand secrets that are not
        # environment variables
        userconf_dir = self._ensure_user_spawnerconf_directory()
        envfile = userconf_dir / "envfile"

        env = self.get_env()
        with StringIO() as content:
            for var, val in sorted(env.items()):
                # The rules for valid shell variables and Python identifiers are
                # similar enough: [a-zA-Z_][0-9a-zA-Z_]*
                if not var.isidentifier():
                    raise StaticSystemdSpawnerError(
                        f"Illegal environment variable {var}. Aborting spawn."
                    )
                content.write(f"{var}={shlex.quote(val)}\n")

            with envfile.open("w") as f:
                os.fchmod(f.fileno(), 0o600)
                f.write(content.getvalue())
        return userconf_dir

    async def start(self):
        self.log.info(
            "user:%s Attempting to start unit %s",
            self.user.name,
            self.unit_name,
        )
        if len(self.unit_name) > 256:
            raise StaticSystemdSpawnerError(
                "Unit name is too long! Please choose a shorter name for the instance."
            )

        # First let's have a look whether the template unit we want to
        # instantiate for the user exists in the first place.
        if not await systemd.unit_exists(self.unit_name):
            if self.unit_generator:
                self.log.info(
                    "user:%s Unit %s does not exist yet. Generating it.",
                    self.user.name,
                    self.unit_name,
                )
                generator_unit = systemd.fill_template_name(self.unit_generator, self.user.name)
                await systemd.start_service(generator_unit)
                if not await systemd.unit_exists(self.unit_name):
                    raise StaticSystemdSpawnerError(
                        f"Cannot spawn JupyterHub because no unit {self.unit_name} exists for your user and could not be generated. "
                        "Please contact your administrator."
                    )
            else:
                raise StaticSystemdSpawnerError(
                    f"Cannot spawn JupyterHub because no unit {self.unit_name} exists for your user. "
                    "Please contact your administrator."
                )

        self.port = random_port()
        self.log.info(
            "user:%s Using port %s to start spawning user server %s",
            self.user.name,
            self.port,
            self.name,
        )

        # If there's a unit with this name running already. This means a bug in
        # JupyterHub, a remnant from a previous install or a failed service start
        # from earlier. Regardless, we kill it and start ours in its place.
        # FIXME: Carefully look at this when doing a security sweep.
        if await systemd.service_running(self.unit_name):
            self.log.info(
                "user:%s Unit %s already exists but not known to JupyterHub. Killing",
                self.user.name,
                self.unit_name,
            )
            await systemd.stop_service(self.unit_name)
            if await systemd.service_running(self.unit_name):
                self.log.error(
                    "Could not stop already existing unit %s",
                    self.unit_name,
                )
                raise StaticSystemdSpawnerError(
                    f"Could not stop already existing unit {self.unit_name}"
                )

        # If there's a unit with this name already but sitting in a failed state.
        # Does a reset of the state before trying to start it up again.
        if await systemd.service_failed(self.unit_name):
            self.log.info(
                "Unit %s in a failed state. Resetting state.",
                self.unit_name,
            )
            await systemd.reset_service(self.unit_name)

        self.unit_secrets_path = self._write_unit_secrets()
        await systemd.start_service(self.unit_name)

        for i in range(self.start_timeout):
            is_up = await self.poll()
            if is_up is None:
                return (self.ip or "127.0.0.1", self.port)
            await asyncio.sleep(1)

        # At this point something went wrong and the start timed
        # out. Let's clean up the secrets to be safe.
        self.log.info(
            "user:%s Spawning unit %s failed. Removing secrets %s",
            self.user.name,
            self.Unit_name,
            self.unit_secrets_path,
        )
        if self.unit_secrets_path:
            try:
                shutil.rmtree(self.unit_secrets_path)
            except FileNotFoundError:
                self.log.info(
                    "user:%s Could not remove secrets for unit %s at %s because they were already missing.",
                    self.user.name,
                    self.unit_name,
                    self.unit_secrets_path,
                )
        return None

    async def stop(self, now=False):
        self.log.info(
            "user:%s Stopping unit %s",
            self.user.name,
            self.unit_name,
        )
        await systemd.stop_service(self.unit_name)
        if self.unit_secrets_path:
            self.log.info(
                "user:%s Removing secrets for unit %s at %s",
                self.user.name,
                self.unit_name,
                self.unit_secrets_path,
            )
            try:
                shutil.rmtree(self.unit_secrets_path)
            except FileNotFoundError:
                self.log.info(
                    "user:%s Could not remove secrets for unit %s at %s because they were already missing.",
                    self.user.name,
                    self.unit_name,
                    self.unit_secrets_path,
                )


    async def poll(self):
        if await systemd.service_running(self.unit_name):
            return None
        return 1
