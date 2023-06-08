# Changelog

## v1.0

### v1.0.1 - 2023-06-08

#### Bugs fixed

- ensure executable paths are absolute [#129](https://github.com/jupyterhub/systemdspawner/pull/129) ([@minrk](https://github.com/minrk), [@consideRatio](https://github.com/consideRatio), [@behrmann](https://github.com/behrmann), [@manics](https://github.com/manics))

#### Maintenance and upkeep improvements

- Use warnings.warn instead of self.log.warning to help avoid duplications [#133](https://github.com/jupyterhub/systemdspawner/pull/133) ([@consideRatio](https://github.com/consideRatio), [@minrk](https://github.com/minrk))
- Cache check of systemd version [#132](https://github.com/jupyterhub/systemdspawner/pull/132) ([@consideRatio](https://github.com/consideRatio), [@minrk](https://github.com/minrk))

#### Contributors to this release

The following people contributed discussions, new ideas, code and documentation contributions, and review.
See [our definition of contributors](https://github-activity.readthedocs.io/en/latest/#how-does-this-tool-define-contributions-in-the-reports).

@behrmann ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fsystemdspawner+involves%3Abehrmann+updated%3A2023-06-01..2023-06-08&type=Issues)) | @consideRatio ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fsystemdspawner+involves%3AconsideRatio+updated%3A2023-06-01..2023-06-08&type=Issues)) | @manics ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fsystemdspawner+involves%3Amanics+updated%3A2023-06-01..2023-06-08&type=Issues)) | @minrk ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fsystemdspawner+involves%3Aminrk+updated%3A2023-06-01..2023-06-08&type=Issues))

### v1.0.0 - 2023-06-01

#### Breaking changes

- Systemd v243+ is now required, and v245+ is recommended. Systemd v245 is
  available in for example Ubuntu 20.04+, Debian 11+, and Rocky/CentOS 9+.
- Python 3.8+, JupyterHub 2.3.0+, and Tornado 5.1+ is now required.
- `SystemdSpawner.disable_user_sudo` (influences systemd's `NoNewPrivileges`)
  now defaults to `True`, making the installation more secure by default.

#### Maintenance and upkeep improvements

- Replace deprecated MemoryLimit with MemoryMax, remove fixme notes [#127](https://github.com/jupyterhub/systemdspawner/pull/127) ([@consideRatio](https://github.com/consideRatio), [@yuvipanda](https://github.com/yuvipanda), [@behrmann](https://github.com/behrmann))
- Rely on systemd-run's --working-directory, and refactor for readability [#124](https://github.com/jupyterhub/systemdspawner/pull/124) ([@consideRatio](https://github.com/consideRatio), [@behrmann](https://github.com/behrmann), [@minrk](https://github.com/minrk))
- Add MANIFEST.in to bundle LICENSE in source distribution [#122](https://github.com/jupyterhub/systemdspawner/pull/122) ([@consideRatio](https://github.com/consideRatio), [@yuvipanda](https://github.com/yuvipanda))
- Add basic start/stop test against a jupyterhub [#120](https://github.com/jupyterhub/systemdspawner/pull/120) ([@consideRatio](https://github.com/consideRatio), [@minrk](https://github.com/minrk), [@yuvipanda](https://github.com/yuvipanda))
- refactor: remove no longer needed pytest.mark.asyncio [#119](https://github.com/jupyterhub/systemdspawner/pull/119) ([@consideRatio](https://github.com/consideRatio), [@yuvipanda](https://github.com/yuvipanda))
- Require systemd v243+, recommend systemd v245+, test against systemd v245 [#117](https://github.com/jupyterhub/systemdspawner/pull/117) ([@consideRatio](https://github.com/consideRatio), [@yuvipanda](https://github.com/yuvipanda), [@minrk](https://github.com/minrk))
- Add test and release automation [#115](https://github.com/jupyterhub/systemdspawner/pull/115) ([@consideRatio](https://github.com/consideRatio), [@yuvipanda](https://github.com/yuvipanda))
- maint, breaking: require python 3.8+, jupyterhub 2.3.0+, tornado 5.1+ [#114](https://github.com/jupyterhub/systemdspawner/pull/114) ([@consideRatio](https://github.com/consideRatio), [@yuvipanda](https://github.com/yuvipanda))
- Add pre-commit for automated formatting [#108](https://github.com/jupyterhub/systemdspawner/pull/108) ([@consideRatio](https://github.com/consideRatio), [@yuvipanda](https://github.com/yuvipanda))
- Disable user sudo by default [#91](https://github.com/jupyterhub/systemdspawner/pull/91) ([@yuvipanda](https://github.com/yuvipanda), [@consideRatio](https://github.com/consideRatio))

#### Documentation improvements

- docs: add some explanatory notes in files, and small details [#118](https://github.com/jupyterhub/systemdspawner/pull/118) ([@consideRatio](https://github.com/consideRatio), [@yuvipanda](https://github.com/yuvipanda))
- readme: add badges for releases/tests/coverage/issues/discourse [#112](https://github.com/jupyterhub/systemdspawner/pull/112) ([@consideRatio](https://github.com/consideRatio), [@yuvipanda](https://github.com/yuvipanda))
- readme: remove resources section and link to discourse forum instead of mailing list [#111](https://github.com/jupyterhub/systemdspawner/pull/111) ([@consideRatio](https://github.com/consideRatio), [@yuvipanda](https://github.com/yuvipanda))

#### Continuous integration improvements

- ci: add dependabot to bump future github actions [#113](https://github.com/jupyterhub/systemdspawner/pull/113) ([@consideRatio](https://github.com/consideRatio), [@yuvipanda](https://github.com/yuvipanda))

#### Contributors to this release

The following people contributed discussions, new ideas, code and documentation contributions, and review.
See [our definition of contributors](https://github-activity.readthedocs.io/en/latest/#how-does-this-tool-define-contributions-in-the-reports).

([GitHub contributors page for this release](https://github.com/jupyterhub/systemdspawner/graphs/contributors?from=2023-01-11&to=2023-06-01&type=c))

@astro-arphid ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fsystemdspawner+involves%3Aastro-arphid+updated%3A2023-01-11..2023-06-01&type=Issues)) | @behrmann ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fsystemdspawner+involves%3Abehrmann+updated%3A2023-01-11..2023-06-01&type=Issues)) | @clhedrick ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fsystemdspawner+involves%3Aclhedrick+updated%3A2023-01-11..2023-06-01&type=Issues)) | @consideRatio ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fsystemdspawner+involves%3AconsideRatio+updated%3A2023-01-11..2023-06-01&type=Issues)) | @manics ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fsystemdspawner+involves%3Amanics+updated%3A2023-01-11..2023-06-01&type=Issues)) | @minrk ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fsystemdspawner+involves%3Aminrk+updated%3A2023-01-11..2023-06-01&type=Issues)) | @yuvipanda ([activity](https://github.com/search?q=repo%3Ajupyterhub%2Fsystemdspawner+involves%3Ayuvipanda+updated%3A2023-01-11..2023-06-01&type=Issues))

## v0.17 - 2023-01-10

- Don't kill whole server when a single process OOMs,
  thanks to [@dragz](https://github.com/dragz) - [PR #101](https://github.com/jupyterhub/systemdspawner/pull/101)

## v0.16 - 2022-04-22

- User variables (like `{USERNAME}`) are expanded in `unit_extra_parameters`,
  thanks to [@tullis](https://github.com/tullis) - [PR #83](https://github.com/jupyterhub/systemdspawner/pull/83)
- Some cleanup of packaging metadata, thanks to [@minrk](https://github.com/minrk) -
  [PR #75](https://github.com/jupyterhub/systemdspawner/pull/75)

## v0.15 - 2020-12-07

Fixes vulnerability [GHSA-cg54-gpgr-4rm6](https://github.com/jupyterhub/systemdspawner/security/advisories/GHSA-cg54-gpgr-4rm6) affecting all previous releases.

- Use EnvironmentFile to pass environment variables to units.

## v0.14 - 2020-07-20

- define entrypoints for JupyterHub spawner configuration
- Fixes for CentOS 7

## v0.13 - 2019-04-28

### Bug Fixes

- Fix `slice` support by making it a configurable option

## v0.12 - 2019-04-17

### New Features

- Allow setting which **Systemd Slice** users' services should belong to.
  This lets admins set policy for all JupyterHub users in one go.
  [Thanks to [@mariusvniekerk](https://github.com/mariusvniekerk)]

### Bug Fixes

- Handle failed units that need reset.
  [thanks to [@RohitK89](https://github.com/RohitK89)]
- Fix bug in cleaning up services from a previously running
  JupyterHub. [thanks to [@minrk](https://github.com/minrk)]

## v0.11 - 2018-07-12

### New Features

- **Username templates** let you map jupyterhub usernames to different system usernames. Extremely
  useful for prefixing usernames to prevent collisions.

### Bug fixes

- Users' home directories now properly read from pwd database, rather than assumed to be under `/home`.
  Thanks to [@cpainterwakefield](https://github.com/cpainterwakefield) for reporting & suggested PR!

## v0.10 - 2018-07-11

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
