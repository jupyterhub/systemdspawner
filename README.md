# systemdspawner

The **systemdspawner** enables JupyterHub to spawn single-user
notebook servers using [systemd](https://www.freedesktop.org/wiki/Software/systemd/).

Additional information about JupyterHub spawners can be found in the
[JupyterHub documentation](https://jupyterhub.readthedocs.io/en/latest/).

## License

We use a shared copyright model that enables all contributors to maintain the
copyright on their contributions.

All code is licensed under the terms of the revised BSD license.

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

## Getting help

We encourage you to ask questions on the [mailing list](https://groups.google.com/forum/#!forum/jupyter),
and you may participate in development discussions or get live help on [Gitter](https://gitter.im/jupyterhub/jupyterhub).

## Resources

- [Reporting Issues](https://github.com/jupyterhub/systemdspawner/issues)
- [Documentation for JupyterHub](http://jupyterhub.readthedocs.io/en/latest/) | [PDF (latest)](https://media.readthedocs.org/pdf/jupyterhub/latest/jupyterhub.pdf) | [PDF (stable)](https://media.readthedocs.org/pdf/jupyterhub/stable/jupyterhub.pdf)
- [Documentation for JupyterHub's REST API](http://petstore.swagger.io/?url=https://raw.githubusercontent.com/jupyter/jupyterhub/master/docs/rest-api.yml#/default)

- [Documentation for Project Jupyter](http://jupyter.readthedocs.io/en/latest/index.html) | [PDF](https://media.readthedocs.org/pdf/jupyter/latest/jupyter.pdf)
- [Project Jupyter website](https://jupyter.org)
