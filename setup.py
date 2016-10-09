from setuptools import setup

setup(
    name='jupyterhub-systemdspawner',
    version='0.1',
    description='JupyterHub Spawner using systemd for resource isolation',
    url='https://github.com/jupyterhub/systemdspawner',
    author='Yuvi Panda',
    author_email='yuvipanda@gmail.com',
    license='3 Clause BSD',
    packages=['systemdspawner'],
    install_requires=['jupyterhub']
)
