from jupyterhub.tests.mocking import public_url
from jupyterhub.tests.test_api import add_user, api_request
from jupyterhub.utils import url_path_join
from tornado.httpclient import AsyncHTTPClient

from systemdspawner import systemd


async def test_start_stop(hub_app, systemdspawner_config, pytestconfig):
    """
    Starts a user server, verifies access to its /api/status endpoint, and stops
    the server.

    This test is skipped unless pytest is passed --system-test-user=USERNAME.
    The started user server process will run as the user in the user's home
    folder, which perhaps is fine, but maybe not.

    About using the root and nobody user:

      - A jupyter server started as root will error without the user server being
        passed the --allow-root flag.

      - SystemdSpawner runs the user server with a working directory set to the
        user's home home directory, which for the nobody user is /nonexistent on
        ubunutu.
    """
    username = pytestconfig.getoption("--system-test-user", skip=True)
    unit_name = f"jupyter-{username}-singleuser.service"

    test_config = {}
    systemdspawner_config.merge(test_config)
    app = await hub_app(systemdspawner_config)

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
    assert await systemd.service_running(unit_name)

    # verify the server is started by accessing the server's api/status
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
    assert not await systemd.service_running(unit_name)
