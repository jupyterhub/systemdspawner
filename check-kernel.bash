#!/bin/bash

# Partially stolen from https://github.com/docker/docker/blob/master/contrib/check-config.sh

possibleConfigs=(
    '/proc/config.gz'
    "/boot/config-$(uname -r)"
    "/usr/src/linux-$(uname -r)/.config"
    '/usr/src/linux/.config'
)

for tryConfig in "${possibleConfigs[@]}"; do
    if [ -e "$tryConfig" ]; then
        CONFIG="$tryConfig"
        break
    fi
done
if [ ! -e "$CONFIG" ]; then
    echo "error: cannot find kernel config"
    echo "please file an issue at https://github.com/jupyterhub/systemdspawner to help us fix this!"
    exit -1
fi

# Check if memory cgroups are enabled
if grep -q 'CONFIG_MEMCG=y' "$CONFIG"; then
    echo "Memory Limiting: Enabled"
else
    echo "Memory Limiting: Disabled"
fi

# Check if cfs scheduling is enabled
if grep -q 'CONFIG_FAIR_GROUP_SCHED=y' "$CONFIG"; then
    echo "CPU Limiting: Enabled"
else
    echo "CPU Limiting: Disabled"
fi
