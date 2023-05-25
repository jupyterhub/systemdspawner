"""
These tests are running JupyterHub configured with a SystemdSpawner and starting
a server for the specific user named "runner". It is not meant to be run outside
a CI system.
"""

import subprocess

import pytest
from jupyterhub.tests.mocking import public_url
from jupyterhub.tests.test_api import add_user, api_request
from jupyterhub.utils import url_path_join
from tornado.httpclient import AsyncHTTPClient


def _get_systemdspawner_user_unit(username):
    """
    Returns an individual SystemdSpawner's created systemd units representing a
    specific user server.

    Note that --output=json is only usable in systemd 246+, so we have to rely
    on this manual parsing.
    """
    unit_name = f"jupyter-{username}-singleuser.service"
    output = subprocess.check_output(
        ["systemctl", "list-units", "--no-pager", "--all", "--plain", unit_name],
        text=True,
    )

    user_unit = output.split("\n")[1].split(maxsplit=4)
    if user_unit[0] != unit_name:
        return None

    # Mimics the output we could get from using --output=json in the future when
    # we can test only against systemd 246+.
    #
    # [
    #     {
    #         "unit": "jupyter-runner-singleuser.service",
    #         "load": "loaded",
    #         "active": "active",
    #         "sub": "running",
    #         "description": "/bin/bash -c cd /home/runner && exec jupyterhub-singleuser "
    #     }
    # ]
    #
    # load   = Reflects whether the unit definition was properly loaded.
    # active = The high-level unit activation state, i.e. generalization of SUB.
    # sub    = The low-level unit activation state, values depend on unit type.
    #
    return {
        "unit": user_unit[0],
        "load": user_unit[1],
        "active": user_unit[2],
        "sub": user_unit[3],
        "description": user_unit[4],
    }


@pytest.mark.github_actions
async def test_start_stop(hub_app, systemdspawner_config):
    """
    This tests starts the default user server, access its /api/status endpoint,
    and stops the server.
    """
    test_config = {}
    systemdspawner_config.merge(test_config)
    app = await hub_app(systemdspawner_config)

    username = "runner"
    add_user(app.db, app, name=username)
    user = app.users[username]

    # start the server with a HTTP POST request to jupyterhub's REST API
    r = await api_request(app, "users", username, "server", method="post")
    pending = r.status_code == 202
    while pending:
        # check server status
        r = await api_request(app, "users", username)
        user_info = r.json()
        pending = user_info["servers"][""]["pending"]
    assert r.status_code in {201, 200}, r.text

    # verify the server is started via systemctl
    user_unit = _get_systemdspawner_user_unit(username)
    assert user_unit
    assert user_unit["load"] == "loaded"
    assert user_unit["active"] == "active"
    assert user_unit["sub"] == "running"

    # very the server is started by accessing the server's api/status
    token = user.new_api_token()
    url = url_path_join(public_url(app, user), "api/status")
    headers = {"Authorization": f"token {token}"}
    resp = await AsyncHTTPClient().fetch(url, headers=headers)
    assert resp.effective_url == url
    resp.rethrow()
    assert "kernels" in resp.body.decode("utf-8")

    # stop the server via a HTTP DELETE request to jupyterhub's REST API
    r = await api_request(app, "users", username, "server", method="delete")
    pending = r.status_code == 202
    while pending:
        # check server status
        r = await api_request(app, "users", username)
        user_info = r.json()
        pending = user_info["servers"][""]["pending"]
    assert r.status_code in {204, 200}, r.text

    # verify the server is stopped via systemctl
    user_unit = _get_systemdspawner_user_unit(username)
    print(user_unit)
    assert not user_unit
