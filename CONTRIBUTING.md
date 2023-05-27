# Contributing

Welcome! As a [Jupyter] project, you can follow the [Jupyter contributor guide].

Make sure to also follow [Project Jupyter's Code of Conduct] for a friendly and
welcoming collaborative environment.

[jupyter]: https://jupyter.org
[project jupyter's code of conduct]: https://github.com/jupyter/governance/blob/HEAD/conduct/code_of_conduct.md
[jupyter contributor guide]: https://jupyter.readthedocs.io/en/latest/contributing/content-contributor.html

## Setting up a local development environment

To setup a local development environment to test changes to systemdspawner
locally, a pre-requisite is to have systemd running in your system environment.
You can check if you do by running `systemctl --version` in a terminal.

Start by setting up Python, Node, and Git by reading the _System requirements_
section in [jupyterhub's contribution guide].

Then do the following:

```shell
# install configurable-http-proxy, a dependency for running a jupyterhub
npm install -g configurable-http-proxy
```

```shell
# clone the systemdspawner github repository to your local computer
git clone https://github.com/jupyterhub/systemdspawner
cd systemdspawner
```

```shell
# install systemdspawner and test dependencies based on code in this folder
pip install --editable ".[test]"
```

We recommend installing `pre-commit` and configuring it to automatically run
autoformatting before you make a git commit. This can be done by:

```shell
# configure pre-commit to help with autoformatting checks before commits are made
pip install pre-commit
pre-commit install --install-hooks
```

[jupyterhub's contribution guide]: https://jupyterhub.readthedocs.io/en/stable/contributing/setup.html#system-requirements

## Running tests

A JupyterHub configured to use SystemdSpawner needs to be run as root, so due to
that we need to run tests as root as well. To still have Python available, we
may need to preserve the PATH when switching to root by using sudo as well, and
perhaps also other environment variables.

```shell
# run pytest as root, preserving environment variables, including PATH
sudo -E "PATH=$PATH" bash -c "pytest"
```

To run all tests, there needs to be a non-root and non-nobody user specified
explicitly via the systemdspawner defined `--system-test-user=USERNAME` flag for
pytest.

```shell
# --system-test-user allows a user server to be started by SystemdSpawner as this
# existing system user, which involves running a user server in the user's home
# directory
sudo -E "PATH=$PATH" bash -c "pytest --system-test-user=USERNAME"
```
