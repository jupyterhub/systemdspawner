from setuptools import setup

with open("README.md") as f:
    long_description = f.read()

setup(
    name="jupyterhub-systemdspawner",
    version="0.16",
    description="JupyterHub Spawner using systemd for resource isolation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/jupyterhub/systemdspawner',
    author='Yuvi Panda',
    author_email='yuvipanda@gmail.com',
    license='3 Clause BSD',
    packages=['systemdspawner'],
    entry_points={
        "jupyterhub.spawners": [
            "systemd = systemdspawner:SystemdSpawner",
            "systemdspawner = systemdspawner:SystemdSpawner",
        ],
    },
    install_requires=[
        "jupyterhub>=0.9",
        "tornado>=5.0",
    ],
)
