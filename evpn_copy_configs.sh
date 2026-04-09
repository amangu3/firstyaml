#!/bin/bash
# Auto-generated: copy configs FROM running containers TO local config/ folder
# Run AFTER: containerlab deploy -t evpn_nobinds.yaml
# Run BEFORE: containerlab destroy -t evpn_nobinds.yaml

set -e

# ── leaf01  (container: clab-evpn-leaf01) ──
docker cp clab-evpn-leaf01:/etc/network/interfaces config/leaf01/interfaces
docker cp clab-evpn-leaf01:/etc/frr/daemons        config/leaf01/daemons
docker cp clab-evpn-leaf01:/etc/frr/frr.conf       config/leaf01/frr.conf

# ── leaf02  (container: clab-evpn-leaf02) ──
docker cp clab-evpn-leaf02:/etc/network/interfaces config/leaf02/interfaces
docker cp clab-evpn-leaf02:/etc/frr/daemons        config/leaf02/daemons
docker cp clab-evpn-leaf02:/etc/frr/frr.conf       config/leaf02/frr.conf

echo "✅ Configs copied from containers for: leaf01, leaf02"
echo "Now run: containerlab destroy -t evpn_nobinds.yaml && containerlab deploy -t evpn.yaml"
