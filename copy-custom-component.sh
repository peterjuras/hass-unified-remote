#!/bin/bash
set -euxo pipefail

rm -rf /usr/share/hassio/homeassistant/custom_components/unified_remote
cp -R custom_components/unified_remote /usr/share/hassio/homeassistant/custom_components/unified_remote
