from setuptools import setup

setup(
    name='jupyterhub-systemdspawner',
    version='0.9.6',
    description='JupyterHub Spawner using systemd for resource isolation',
    long_description='See https://github.com/jupyterhub/systemdspawner for more info',
    url='https://github.com/jupyterhub/systemdspawner',
    author='Yuvi Panda',
    author_email='yuvipanda@gmail.com',
    license='3 Clause BSD',
    packages=['systemdspawner'],
    install_requires=['jupyterhub'],
)
