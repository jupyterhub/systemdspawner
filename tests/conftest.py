import os

import pytest
from traitlets.config import Config

# pytest-jupyterhub provides a pytest-plugin, and from it we get various
# fixtures, where we make use of hub_app that builds on MockHub, which defaults
# to providing a MockSpawner.
#
# ref: https://github.com/jupyterhub/pytest-jupyterhub
# ref: https://github.com/jupyterhub/jupyterhub/blob/4.0.0/jupyterhub/tests/mocking.py#L224
#
pytest_plugins = [
    "jupyterhub-spawners-plugin",
]


def pytest_configure(config):
    """
    A pytest recognized function to adjust configuration before running tests.
    """
    config.addinivalue_line(
        "markers", "github_actions: only to be run in a github actions ci environment"
    )

    # These markers are registered to avoid warnings triggered by importing from
    # jupyterhub.tests.test_api in test_systemspawner.py.
    config.addinivalue_line("markers", "role: dummy")
    config.addinivalue_line("markers", "user: dummy")
    config.addinivalue_line("markers", "slow: dummy")
    config.addinivalue_line("markers", "group: dummy")
    config.addinivalue_line("markers", "services: dummy")


def pytest_runtest_setup(item):
    """
    Several of these tests work against the host system directly, so to protect
    users from issues we make these not run.
    """
    if not os.environ.get("GITHUB_ACTIONS"):
        has_github_actions_mark = any(
            mark for mark in item.iter_markers(name="github_actions")
        )
        if has_github_actions_mark:
            pytest.skip("Skipping test marked safe only for GitHub's CI environment.")


@pytest.fixture
async def systemdspawner_config():
    """
    Represents the base configuration of relevance to test SystemdSpawner.
    """
    config = Config()
    config.JupyterHub.spawner_class = "systemd"
    config.JupyterHub.cookie_secret = "abc123"

    return config
