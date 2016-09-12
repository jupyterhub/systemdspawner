from setuptools import setup

setup(
    name='jupyterhub-systemd-spawner',
    version='0.1',
    description='Spawner using systemd for resource isolation',
    url='https://github.com/yuvipanda/jupyterhub-systemd-spawner',
    author='Yuvi Panda',
    author_email='yuvipanda@riseup.net',
    license='3 Clause BSD',
    packages=['systemdspawner'],
    install_requires=['jupyterhub']
)
