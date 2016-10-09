# systemdspawner #

The **systemdspawner** enables JupyterHub to spawn single-user
notebook servers using [systemd](https://www.freedesktop.org/wiki/Software/systemd/).

## Features ##

The primary use case for the Systemd Spawner is to provide the isolation benefits
of Linux Containers (Docker, rkt, etc) without the complexity of image management.
You also get to use all the traditional system administration tools you know and love,
without having to learn an extra layer of container related tooling. This is very important
for installations upto a certain size.

The following features are currently available:

1. Limit maximum memory available to each user
2. Limit maximum CPU available to each user
3. Provide fair scheduling to users independent of the number of processes they
   are running. For example, user A running 100 CPU hogging processes will usually
   mean user B's 2 CPU hogging processes never get enough CPU time, since scheduling
   is traditionally per-process. With Systemd Spawner, both these users' processes
   will as a whole get the same amount of CPU time, regardless of number of processes.
4. Accurate accounting of memory and CPU usage (via cgroups, which systemd uses internally)
5. `/tmp` isolation (each user gets their own `/tmp`, to prevent accidental information
   leakage)
6. Spawn containers as specific users on the system (this can replace SudoSpawner)
7. Restrict users from being able to sudo to root (or as other users) from within the
   notebook. This is an additional security measure to make sure that a compromise of
   a jupyterhub notebook instance doesn't allow root access from the web.
8. Restrict what paths users can write to. This allows making / readonly and only granting
   write rights to specific paths, for additional security.
9. Automatically collect logs from each individual user notebook into `journald`, which
   also automatically handles rotation & retention.

## Requirements ##

### Systemd ###
Systemd Spawner requires you to use a Linux Distro that ships with at least
systemd v211. We use `systemd-run` to launch notebooks, and it gained the
ability to set service properties in that version. You can check which version of
systemd is running with:

```bash
$ systemd --version | head -1
systemd 231
```
The following distros (and newer versions of them!) should all work fine:

* Ubuntu 16.04
* Debian Jessie
* CentOS 7 and derivatives

### Kernel Configuration ###

Certain kernel options need to be enabled for the CPU / Memory limiting features
to work. If these are not enabled, then CPU / Memory limiting will just fail
silently. You can check if your kernel supports these features by running
the [`check-kernel.bash`](check-kernel.bash) script.

### Root access ###

Currently, JupyterHub must be run as root to use Systemd Spawner. `systemd-run`
needs to be run as root to be able to set memory & cpu limits. Simple sudo rules
do not help, since unrestricted access to `systemd-run` is equivalent to root. We
will explore hardening approaches soon.

### Local Users ###

Each user's server is spawned to run as a local unix user account. Hence this spawner
requires that all users who authenticate have a local account already present on the
machine.

## Installation ##

There is no package on PyPI yet, so you have to install directly from git.
Once there is a stable tested version we'll have a version on PyPI.

You can install it right now with:

```
pip install git+https://github.com/jupyterhub/systemdspawner.git@master
```

You can enable it for your jupyterhub with the following lines in your
`jupyterhub_config.py` file

```python
c.JupyterHub.spawner_class = 'systemdspawner.SystemdSpawner'
```

## Configuration ##

Lots of configuration options to chose from! You can put all of these in your
`jupyterhub_config.py` file.

### `mem_limit` ###

Specifies the maximum memory that can be used by each individual user. It can be
specified as an absolute byte value, or a percentage of total physical memory
on the machine. You can use the suffixes `K`, `M`, `G` or `T` to mean Kilobyte,
Megabyte, Gigabyte or Terabyte respectively. Using a `%` as a suffix makes it
be that % of total physical memory. Setting it to `None` disables memory limits.

Even if you want individual users to use as much memory as possible, it is still
good practice to set a memory limit of 80-90%. This prevents one user from being
able to single handedly take down the machine accidentally by OOMing it.

```python
c.SystemdSpawner.mem_limit = '4G'
```

Defaults to `90%`.

### `cpu_limit` ###

An integer representing the total CPU each user can use. `100` represents one full
CPU, `400` represents 4 full CPUs, `50` represents half of one CPU, etc. This is
the same metric you see in the `top` tool.

```python
c.SystemdSpawner.cpu_limit = 4
```

This defaults to `None`, which provides no CPU limits.

#### CPU fairness ####

Completely unrelated to `cpu_limit` is the concept of CPU fairness - that each
user should have equal access to all the CPUs in the absense of limits. This
does not entirely work in the normal case for Jupyter Notebooks, since CPU
scheduling happens on a per-process level, rather than per-user. This means
a user running 100 processes has 100x more access to the CPU than a user running
1. This is far from an ideal situation.

Since each user's notebook server runs in its own Systemd Service, this problem
is mitigated - all the processes spawned from a user's notebook server are run
in one cgroup, and cgroups are treated equally for CPU scheduling. So independent
of how many processes each user is running, they all get equal access to the CPU.
This works out perfect for most cases, since this allows users to burst up and
use all CPU when nobody else is using CPU & forces them to automatically yield
when other users want to use the CPU.

### `user_workingdir` ###

The directory to spawn each user's notebook server in. This directory is what users
see when they open their notebooks servers. Usually this is the user's home directory.

`{USERNAME}` and `{USERID}` in this configuration value will be expanded to the
appropriate values for the user being spawned.

```python
c.SystemdSpawner.user_workingdir = '/home/{USERNAME}'
```

This defaults to `/home/{USERNAME}`.

### `default_shell` ###

The default shell to use for the terminal in the notebook. Sets the `SHELL` environment
variable to this.

```python
c.SystemdSpawner.default_shell = '/bin/bash'
```
Defaults to whatever the value of the `SHELL` environment variable is in the JupyterHub
process, or `/bin/bash` if `SHELL` isn't set.

### `extra_paths` ###

List of paths that should be added to the `PATH` environment variable for the spawned
notebook server. This is easier than setting the `env` property, since you want to
add to PATH, not completely replace it. Very useful when you want to add a virtualenv
or conda install onto the user's `PATH` by default.

```python
c.SystemdSpawner.extra_paths = ['/home/{USERNAME}/conda/bin']
```

`{USERNAME}` and `{USERID}` in this configuration value will be expanded to the
appropriate values for the user being spawned.

### `unit_name_template` ###

Template to form the Systemd Service unit name for each user notebook server. This
allows differentiating between multiple jupyterhubs with Systemd Spawner on the same
machine. Should contain only [a-zA-Z0-9_-].

```python
c.SystemdSpawner.unit_name_template = 'jupyter-{USERNAME}-singleuser'
```

`{USERNAME}` and `{USERID}` in this configuration value will be expanded to the
appropriate values for the user being spawned.

It defaults to `jupyter-{USERNAME}-singleuser`

### `isolate_tmp` ###

Setting this to true provides a separate, private `/tmp` for each user. This is very
useful to protect against accidental leakage of otherwise private information - it is
possible that libraries / tools you are using create /tmp files without you knowing and
this is leaking info.

```python
c.SystemdSpawner.isolate_tmp = True
```

Defaults to false.

This requires systemd version > 227. If you enable this in earlier versions, spawning will
fail.

### `disable_user_sudo` ###

Setting this to true prevents users from being able to use `sudo` (or any other means) to
become other users (including root). This helps contain damage from a compromise of a user's
credentials if they also have sudo rights on the machine - a web based exploit will now only
be able to damage the user's own stuff, rather than have complete root access.

```python
c.SystemdSpawner.disable_user_sudo = True
```

Defaults to false.

### `readonly_paths` ###

List of filesystem paths that should be mounted readonly for the users' notebook server. This
will override any filesystem permissions that might exist. Subpaths of paths that are mounted
readonly can be marked readwrite with `readwrite_paths`. This is useful for marking `/` as
readonly & only whitelisting the paths where notebook users can write.

```python
c.SystemdSpawner.readonly_paths = ['/']
```

`{USERNAME}` and `{USERID}` in this configuration value will be expanded to the
appropriate values for the user being spawned.

Defaults to `None` which disables this feature.

### `readwrite_paths` ###

List of filesystem paths that should be mounted readwrite for the users' notebook server. This
only makes sense if `readonly_paths` is used to make some paths readonly - this can then be
used to make specific paths readwrite. This does *not* override filesystem permissions - the
user needs to have appropriate rights to write to these paths.

```python
c.SystemdSpawner.readwrite_paths = ['/home/{USERNAME}']
```

`{USERNAME}` and `{USERID}` in this configuration value will be expanded to the
appropriate values for the user being spawned.

Defaults to `None` which disables this feature.

## Getting help

We encourage you to ask questions on the [mailing list](https://groups.google.com/forum/#!forum/jupyter),
and you may participate in development discussions or get live help on [Gitter](https://gitter.im/jupyterhub/jupyterhub).

## License ##

We use a shared copyright model that enables all contributors to maintain the
copyright on their contributions.

All code is licensed under the terms of the revised BSD license.

## Resources

- [Reporting Issues](https://github.com/jupyterhub/systemdspawner/issues)
- [Documentation for JupyterHub](http://jupyterhub.readthedocs.io/en/latest/) | [PDF (latest)](https://media.readthedocs.org/pdf/jupyterhub/latest/jupyterhub.pdf) | [PDF (stable)](https://media.readthedocs.org/pdf/jupyterhub/stable/jupyterhub.pdf)
- [Documentation for JupyterHub's REST API](http://petstore.swagger.io/?url=https://raw.githubusercontent.com/jupyter/jupyterhub/master/docs/rest-api.yml#/default)

- [Documentation for Project Jupyter](http://jupyter.readthedocs.io/en/latest/index.html) | [PDF](https://media.readthedocs.org/pdf/jupyter/latest/jupyter.pdf)
- [Project Jupyter website](https://jupyter.org)
