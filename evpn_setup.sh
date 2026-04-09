#!/bin/bash
# Auto-generated: creates config folders for CVX nodes
# Run this before: containerlab deploy -t evpn.yaml

set -e

# ── leaf01 ──
mkdir -p config/leaf01
touch config/leaf01/interfaces
touch config/leaf01/daemons
touch config/leaf01/frr.conf

# ── leaf02 ──
mkdir -p config/leaf02
touch config/leaf02/interfaces
touch config/leaf02/daemons
touch config/leaf02/frr.conf

echo "✅ Config folders created for: leaf01, leaf02"
