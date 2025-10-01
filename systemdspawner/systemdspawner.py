import asyncio
import os
import pwd
import sys
import warnings

from jupyterhub.spawner import Spawner
from jupyterhub.utils import random_port
from traitlets import Bool, Dict, List, Unicode

from systemdspawner import systemd

SYSTEMD_REQUIRED_VERSION = 243
SYSTEMD_LOWEST_RECOMMENDED_VERSION = 245


class SystemdSpawner(Spawner):
    user_workingdir = Unicode(
        None,
        allow_none=True,
        help="""
        Path to start each notebook user on.

        {USERNAME} and {USERID} are expanded.

        Defaults to the home directory of the user.

        Not respected if dynamic_users is set to True.
        """,
    ).tag(config=True)

    username_template = Unicode(
        "{USERNAME}",
        help="""
        Template for unix username each user should be spawned as.

        {USERNAME} and {USERID} are expanded.

        This user should already exist in the system.

        Not respected if dynamic_users is set to True
        """,
    ).tag(config=True)

    default_shell = Unicode(
        os.environ.get("SHELL", "/bin/bash"),
        help="Default shell for users on the notebook terminal",
    ).tag(config=True)

    extra_paths = List(
        [],
        help="""
        Extra paths to prepend to the $PATH environment variable.

        {USERNAME} and {USERID} are expanded
        """,
    ).tag(config=True)

    unit_name_template = Unicode(
        "jupyter-{USERNAME}-singleuser",
        help="""
        Template to use to make the systemd service names.

        {USERNAME} and {USERID} are expanded}
        """,
    ).tag(config=True)

    isolate_tmp = Bool(
        False,
        help="""
        Give each notebook user their own /tmp, isolated from the system & each other
        """,
    ).tag(config=True)

    isolate_devices = Bool(
        False,
        help="""
        Give each notebook user their own /dev, with a very limited set of devices mounted
        """,
    ).tag(config=True)

    disable_user_sudo = Bool(
        True,
        help="""
        Set to true to disallow becoming root (or any other user) via sudo or other means from inside the notebook
        """,
    ).tag(config=True)

    readonly_paths = List(
        None,
        allow_none=True,
        help="""
        List of paths that should be marked readonly from the user notebook.

        Subpaths maybe be made writeable by setting readwrite_paths
        """,
    ).tag(config=True)

    readwrite_paths = List(
        None,
        allow_none=True,
        help="""
        List of paths that should be marked read-write from the user notebook.

        Used to make a subpath of a readonly path writeable
        """,
    ).tag(config=True)

    unit_extra_properties = Dict(
        {},
        help="""
        Dict of extra properties for systemd-run --property=[...].

        Keys are property names, and values are either strings or
        list of strings (for multiple entries). When values are
        lists, ordering is guaranteed. Ordering across keys of the
        dictionary are *not* guaranteed.

        Used to add arbitrary properties for spawned Jupyter units.
        Read `man systemd-run` for details on per-unit properties
        available in transient units.
        """,
    ).tag(config=True)

    dynamic_users = Bool(
        False,
        help="""
        Allocate system users dynamically for each user.

        Uses the DynamicUser= feature of Systemd to make a new system user
        for each hub user dynamically. Their home directories are set up
        in the state directories configured by the dynamic_user_statedir
        option, and persist over time. The system user is deallocated whenever
        the user's server is not running.

        See http://0pointer.net/blog/dynamic-users-with-systemd.html for more
        information.
        """,
    ).tag(config=True)

    dynamic_user_statedir = Unicode(
        "{USERNAME}",
        help="""
        The state directory for dynamic users. This is the name of a persistent
        directory under /var/lib.

        {USERNAME} and {USERID} are expanded.

        Defaults to {USERNAME}, corresponding to a filesystem directory
        /var/lib/{USERNAME}.

        Ignored if dynamic_users is set to False.
        """,
    ).tag(config=True)

    slice = Unicode(
        None,
        allow_none=True,
        help="""
        Ensure that all users that are created are run within a given slice.
        This allow global configuration of the maximum resources that all users
        collectively can use by creating a a slice beforehand.
        """,
    ).tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # All traitlets configurables are configured by now
        self.unit_name = self._expand_user_vars(self.unit_name_template)

        self.log.debug(
            "user:%s Initialized spawner with unit %s", self.user.name, self.unit_name
        )

        systemd_version = systemd.get_systemd_version()
        if systemd_version is None:
            # not found, nothing to check
            # already warned about this in get_systemd_version
            pass
        elif systemd_version < SYSTEMD_REQUIRED_VERSION:
            self.log.critical(
                f"systemd version {SYSTEMD_REQUIRED_VERSION} or higher is required, version {systemd_version} is used"
            )
            sys.exit(1)
        elif systemd_version < SYSTEMD_LOWEST_RECOMMENDED_VERSION:
            warnings.warn(
                f"systemd version {SYSTEMD_LOWEST_RECOMMENDED_VERSION} or higher is recommended, version {systemd_version} is used"
            )

    def _expand_user_vars(self, string):
        """
        Expand user related variables in a given string

        Currently expands:
          {USERNAME} -> Name of the user
          {USERID} -> UserID
        """
        return string.format(USERNAME=self.user.name, USERID=self.user.id)

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

    async def start(self):
        self.port = random_port()
        self.log.debug(
            "user:%s Using port %s to start spawning user server",
            self.user.name,
            self.port,
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
                    "user:%s Could not stop already existing unit %s",
                    self.user.name,
                    self.unit_name,
                )
                raise Exception(
                    f"Could not stop already existing unit {self.unit_name}"
                )

        # If there's a unit with this name already but sitting in a failed state.
        # Does a reset of the state before trying to start it up again.
        if await systemd.service_failed(self.unit_name):
            self.log.info(
                "user:%s Unit %s in a failed state. Resetting state.",
                self.user.name,
                self.unit_name,
            )
            await systemd.reset_service(self.unit_name)

        env = self.get_env()

        properties = {}

        if self.dynamic_users:
            properties["DynamicUser"] = "yes"

            # Expand the state directory for the unit. Perform some basic checks on the
            # directory name so we can give a more obvious error than systemd would.
            statedir = self._expand_user_vars(self.dynamic_user_statedir)
            if os.path.isabs(statedir):
                self.log.error(
                    "User %s: StateDirectory (%s) cannot be absolute",
                    self.user.name,
                    statedir,
                )
                raise Exception(f"StateDirectory ({statedir}) cannot be absolute")

            testpath = statedir
            while testpath:
                testpath, component = os.path.split(testpath)
                if component == "..":
                    self.log.error(
                        "User %s: StateDirectory (%s) cannot contain ..",
                        self.user.name,
                        statedir,
                    )
                    raise Exception(f"StateDirectory ({statedir}) cannot contain ..")

            properties["StateDirectory"] = statedir

            # HOME is not set by default otherwise. Systemd places the state
            # directory under /var/lib.
            env["HOME"] = f"/var/lib/{statedir}"
            # Set working directory to $HOME too
            working_dir = env["HOME"]
            # Set uid, gid = None so we don't set them
            uid = gid = None
        else:
            try:
                unix_username = self._expand_user_vars(self.username_template)
                pwnam = pwd.getpwnam(unix_username)
            except KeyError:
                self.log.exception(f"No user named {unix_username} found in the system")
                raise
            uid = pwnam.pw_uid
            gid = pwnam.pw_gid
            if self.user_workingdir is None:
                working_dir = pwnam.pw_dir
            else:
                working_dir = self._expand_user_vars(self.user_workingdir)

        if self.isolate_tmp:
            properties["PrivateTmp"] = "yes"

        if self.isolate_devices:
            properties["PrivateDevices"] = "yes"

        if self.extra_paths:
            new_path_list = [self._expand_user_vars(p) for p in self.extra_paths]
            current_or_default_path = env.get("PATH", os.defpath)
            if current_or_default_path:
                new_path_list.append(current_or_default_path)
            env["PATH"] = ":".join(new_path_list)

        env["SHELL"] = self.default_shell

        if self.mem_limit is not None:
            properties["MemoryAccounting"] = "yes"
            properties["MemoryMax"] = self.mem_limit

        if self.cpu_limit is not None:
            # NOTE: The linux kernel must be compiled with the configuration option
            #       CONFIG_CFS_BANDWIDTH, otherwise CPUQuota doesn't have any
            #       effect.
            #
            #       This can be checked with the check-kernel.bash script in
            #       this git repository.
            #
            #       ref: https://github.com/systemd/systemd/blob/v245/README#L35
            #
            properties["CPUAccounting"] = "yes"
            properties["CPUQuota"] = f"{int(self.cpu_limit * 100)}%"

        if self.disable_user_sudo:
            properties["NoNewPrivileges"] = "yes"

        if self.readonly_paths is not None:
            properties["ReadOnlyDirectories"] = [
                self._expand_user_vars(path) for path in self.readonly_paths
            ]

        if self.readwrite_paths is not None:
            properties["ReadWriteDirectories"] = [
                self._expand_user_vars(path) for path in self.readwrite_paths
            ]

        for property, value in self.unit_extra_properties.items():
            self.unit_extra_properties[property] = self._expand_user_vars(value)

        properties.update(self.unit_extra_properties)

        await systemd.start_transient_service(
            self.unit_name,
            cmd=[self._expand_user_vars(c) for c in self.cmd],
            args=[self._expand_user_vars(a) for a in self.get_args()],
            working_dir=working_dir,
            environment_variables=env,
            properties=properties,
            uid=uid,
            gid=gid,
            slice=self.slice,
        )

        for i in range(self.start_timeout):
            is_up = await self.poll()
            if is_up is None:
                return (self.ip or "127.0.0.1", self.port)
            await asyncio.sleep(1)

        return None

    async def stop(self, now=False):
        await systemd.stop_service(self.unit_name)

    async def poll(self):
        if await systemd.service_running(self.unit_name):
            return None
        return 1
