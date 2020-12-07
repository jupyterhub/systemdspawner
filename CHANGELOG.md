# Changelog

## v0.15

Fixes vulnerability [GHSA-cg54-gpgr-4rm6](https://github.com/jupyterhub/systemdspawner/security/advisories/GHSA-cg54-gpgr-4rm6) affecting all previous releases.

- Use EnvironmentFile to pass environment variables to units.

## v0.14

- define entrypoints for JupyterHub spawner configuration
- Fixes for CentOS 7

## v0.13

### Bug Fixes

- Fix `slice` support by making it a configurable option

## v0.12

### New Features

- Allow setting which **Systemd Slice** users' services should belong to.
  This lets admins set policy for all JupyterHub users in one go.
  [Thanks to [@mariusvniekerk](https://github.com/mariusvniekerk)]

### Bug Fixes

- Handle failed units that need reset.
  [thanks to [@RohitK89](https://github.com/RohitK89)]
- Fix bug in cleaning up services from a previously running
  JupyterHub. [thanks to [@minrk](https://github.com/minrk)]

## v0.11

### New Features

- **Username templates** let you map jupyterhub usernames to different system usernames. Extremely
  useful for prefixing usernames to prevent collisions.

### Bug fixes

- Users' home directories now properly read from pwd database, rather than assumed to be under `/home`.
  Thanks to [@cpainterwakefield](https://github.com/cpainterwakefield) for reporting & suggested PR!

## v0.10

### Breaking changes

- `use_sudo` option is no longer supported. It offered questionable security,
  and complicated the code unnecessarily. If 'securely run as normal user with
  sudo' is a required feature, we can re-implement it securely later.
- If a path in `readonly_paths` does not exist, spawning user will now fail.

### New features

- **Dynamic users** support, creating users as required with their own
  persistent homes with systemd's [dynamic users](http://0pointer.net/blog/dynamic-users-with-systemd.html)
  feature. Useful for using with tmpnb.
- **Add additional properties** to the user's systemd unit with `unit_extra_properties`.
  Thanks to [@kfix](https://github.com/kfix) for most of the work!

### Bug fixes

- If a user's notebook server service is already running, kill it before
  attempting to start a new one. [GitHub Issue](https://github.com/jupyterhub/systemdspawner/issues/7)

### Dependency changes

- Python 3.5 is the minimum supported Python version.
- JupyterHub 0.9 is the minimum supported JupyterHub version.
- Tornado 5.0 is the minimum supported Tornado version.
