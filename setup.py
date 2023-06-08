from setuptools import setup

with open("README.md") as f:
    long_description = f.read()

setup(
    name="jupyterhub-systemdspawner",
    version="1.0.2.dev",
    description="JupyterHub Spawner using systemd for resource isolation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jupyterhub/systemdspawner",
    author="Yuvi Panda",
    author_email="yuvipanda@gmail.com",
    license="3 Clause BSD",
    packages=["systemdspawner"],
    entry_points={
        "jupyterhub.spawners": [
            "systemd = systemdspawner:SystemdSpawner",
            "systemdspawner = systemdspawner:SystemdSpawner",
        ],
    },
    python_requires=">=3.8",
    install_requires=[
        "jupyterhub>=2.3.0",
        "tornado>=5.1",
    ],
    extras_require={
        "test": [
            "pytest",
            "pytest-asyncio",
            "pytest-cov",
            "pytest-jupyterhub",
        ],
    },
)
