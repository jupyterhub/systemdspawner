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


def pytest_addoption(parser, pluginmanager):
    """
    A pytest hook to register argparse-style options and ini-style config
    values.

    We use it to declare command-line arguments.

    ref: https://docs.pytest.org/en/stable/reference/reference.html#pytest.hookspec.pytest_addoption
    ref: https://docs.pytest.org/en/stable/reference/reference.html#pytest.Parser.addoption
    """
    parser.addoption(
        "--system-test-user",
        help="Test server spawning for this existing system user",
    )


def pytest_configure(config):
    """
    A pytest hook to adjust configuration before running tests.

    We use it to declare pytest marks.

    ref: https://docs.pytest.org/en/stable/reference/reference.html#pytest.hookspec.pytest_configure
    ref: https://docs.pytest.org/en/stable/reference/reference.html#pytest.Config
    """
    # These markers are registered to avoid warnings triggered by importing from
    # jupyterhub.tests.test_api in test_systemspawner.py.
    config.addinivalue_line("markers", "role: dummy")
    config.addinivalue_line("markers", "user: dummy")
    config.addinivalue_line("markers", "slow: dummy")
    config.addinivalue_line("markers", "group: dummy")
    config.addinivalue_line("markers", "services: dummy")


@pytest.fixture
async def systemdspawner_config():
    """
    Represents the base configuration of relevance to test SystemdSpawner.
    """
    config = Config()
    config.JupyterHub.spawner_class = "systemd"

    # set cookie_secret to avoid having jupyterhub create a file
    config.JupyterHub.cookie_secret = "abc123"

    return config
