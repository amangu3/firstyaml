import random
import ipaddress
import os

def pick_random_ip(subnet: str, used: set) -> str:
    net = ipaddress.IPv4Network(subnet, strict=False)
    hosts = [str(h) for h in net.hosts()]
    available = [h for h in hosts if h not in used]
    if not available:
        raise RuntimeError("No free IPs left in subnet!")
    ip = random.choice(available)
    used.add(ip)
    return ip

def ask(prompt: str) -> str:
    return input(prompt).strip()

def ask_int(prompt: str) -> int:
    while True:
        try:
            return int(ask(prompt))
        except ValueError:
            print("  ❌  Please enter a valid number.")

def next_iface(node: str, node_types: dict, iface_counters: dict) -> str:
    """Auto assign next interface based on node type."""
    kind = node_types.get(node, "cvx")
    if node not in iface_counters:
        iface_counters[node] = 1
    idx = iface_counters[node]
    iface_counters[node] += 1
    if kind == "linux":
        return f"eth{idx}"
    else:  # cvx
        return f"swp{idx}"

def main():
    print("\n╔══════════════════════════════════════════╗")
    print("║   Containerlab Topology YAML Generator   ║")
    print("╚══════════════════════════════════════════╝\n")

    used_ips: set = set()
    node_types: dict = {}      # node_name → "cvx" | "linux"
    iface_counters: dict = {}  # node_name → next interface index

    # ── Basic info ────────────────────────────────────────────────────────────
    yaml_filename = ask("📄  YAML file name (e.g. topology.yaml): ")
    if not yaml_filename.endswith(".yaml") and not yaml_filename.endswith(".yml"):
        yaml_filename += ".yaml"

    lab_name     = ask("🏷️   Lab name (e.g. citc): ")
    mgmt_network = ask("🌐  Mgmt network name (default: mgmt): ") or "mgmt"
    mgmt_subnet  = ask("📡  Mgmt IPv4 subnet (e.g. 172.20.20.0/24): ")

    nodes = {}  # ordered dict for yaml output

    # ── CVX Nodes ─────────────────────────────────────────────────────────────
    print("\n── CVX Nodes (switches) ──────────────────────────────────────")
    num_nodes = ask_int("🔢  Number of CVX nodes: ")

    for i in range(num_nodes):
        print(f"\n  Node {i+1}:")
        node_name = ask("    Name (e.g. spine01): ")
        mgmt_ip   = pick_random_ip(mgmt_subnet, used_ips)
        print(f"    ✅ Assigned mgmt-ipv4: {mgmt_ip}")
        node_types[node_name] = "cvx"
        nodes[node_name] = {
            "kind": "cvx",
            "image": "networkop/cx:4.4.0",
            "mgmt-ipv4": mgmt_ip,
            "binds": [
                f"config/{node_name}/interfaces:/etc/network/interfaces",
                f"config/{node_name}/daemons:/etc/frr/daemons",
                f"config/{node_name}/frr.conf:/etc/frr/frr.conf",
            ],
        }

    # ── Linux Servers ─────────────────────────────────────────────────────────
    print("\n── Linux Servers ─────────────────────────────────────────────")
    num_servers = ask_int("🔢  Number of servers: ")

    for i in range(num_servers):
        print(f"\n  Server {i+1}:")
        srv_name = ask("    Name (e.g. server01): ")
        mgmt_ip  = pick_random_ip(mgmt_subnet, used_ips)
        print(f"    ✅ Assigned mgmt-ipv4: {mgmt_ip}")
        node_types[srv_name] = "linux"
        nodes[srv_name] = {
            "kind": "linux",
            "image": "alpine:latest",
            "mgmt-ipv4": mgmt_ip,
        }

    all_nodes = list(nodes.keys())

    # ── Links ─────────────────────────────────────────────────────────────────
    print("\n── Links ─────────────────────────────────────────────────────")
    print("  For each node, enter the nodes it connects TO (one per line).")
    print("  Interfaces will be auto-assigned (cvx→swp, server→eth).")
    print("  Type 'done' to finish connections for that node.\n")

    links = []  # list of {ep1, ep2}
    # track already added pairs to avoid duplicates
    added_pairs = set()

    for node in all_nodes:
        print(f"\n  🔌 Connections for '{node}' (type peer node name, or 'skip'):")
        while True:
            peer = ask(f"    {node} → ").strip()
            if peer.lower() in ("done", "skip", ""):
                break
            if peer not in node_types:
                print(f"    ❌  '{peer}' not found. Available: {', '.join(all_nodes)}")
                continue
            if peer == node:
                print("    ❌  Node cannot connect to itself.")
                continue

            # avoid duplicate links (a-b same as b-a)
            pair = tuple(sorted([node, peer]))
            if pair in added_pairs:
                print(f"    ⚠️   Link {node} ↔ {peer} already added, skipping.")
                continue

            added_pairs.add(pair)

            iface1 = next_iface(node, node_types, iface_counters)
            iface2 = next_iface(peer, node_types, iface_counters)
            ep1 = f"{node}:{iface1}"
            ep2 = f"{peer}:{iface2}"
            links.append({"ep1": ep1, "ep2": ep2})
            print(f"    ✅  Added: [\"{ep1}\", \"{ep2}\"]")

    script_dir  = os.path.dirname(os.path.abspath(__file__))
    base_name   = yaml_filename.replace(".yaml", "").replace(".yml", "")
    cvx_nodes   = [n for n, v in nodes.items() if v["kind"] == "cvx"]

    # ── Helper: build YAML lines ───────────────────────────────────────────────
    def build_yaml(include_binds: bool) -> str:
        lines = []
        lines.append(f"name: {lab_name}")
        lines.append("mgmt:")
        lines.append(f"  network: {mgmt_network}")
        lines.append(f"  ipv4-subnet: {mgmt_subnet}")
        lines.append("topology:")
        lines.append("  nodes:")

        for nname, nval in nodes.items():
            lines.append(f"    {nname}:")
            lines.append(f"      kind: {nval['kind']}")
            lines.append(f"      image: {nval['image']}")
            lines.append(f"      mgmt-ipv4: {nval['mgmt-ipv4']}")
            if include_binds and "binds" in nval:
                lines.append("      binds:")
                for b in nval["binds"]:
                    lines.append(f"      - {b}")

        lines.append("  links:")
        for lnk in links:
            lines.append(f'    - endpoints: ["{lnk["ep1"]}", "{lnk["ep2"]}"]')

        return "\n".join(lines) + "\n"

    # ── File 1: topology WITH binds ───────────────────────────────────────────
    yaml_with    = base_name + ".yaml"
    path_with    = os.path.join(script_dir, yaml_with)
    content_with = build_yaml(include_binds=True)
    with open(path_with, "w") as f:
        f.write(content_with)
    print(f"\n{'─'*55}")
    print(f"📄 FILE 1 — WITH binds → {yaml_with}")
    print(f"{'─'*55}")
    print(content_with)

    # ── File 2: topology WITHOUT binds ────────────────────────────────────────
    yaml_nobinds    = base_name + "_nobinds.yaml"
    path_nobinds    = os.path.join(script_dir, yaml_nobinds)
    content_nobinds = build_yaml(include_binds=False)
    with open(path_nobinds, "w") as f:
        f.write(content_nobinds)
    print(f"📄 FILE 2 — WITHOUT binds → {yaml_nobinds}")
    print(f"{'─'*55}")
    print(content_nobinds)

    # ── File 3: shell script ──────────────────────────────────────────────────
    shell_filename = base_name + "_setup.sh"
    shell_path     = os.path.join(script_dir, shell_filename)

    sh = []
    sh.append("#!/bin/bash")
    sh.append("# Auto-generated: creates config folders and empty files for CVX nodes")
    sh.append("# Run this before: containerlab deploy -t " + yaml_with)
    sh.append("")
    sh.append("set -e")
    sh.append("")

    for nname in cvx_nodes:
        sh.append(f"# ── {nname} ──")
        sh.append(f"mkdir -p config/{nname}")
        sh.append(f"touch config/{nname}/interfaces")
        sh.append(f"touch config/{nname}/daemons")
        sh.append(f"touch config/{nname}/frr.conf")
        sh.append("")

    sh.append(f'echo "✅ Config folders created for: {", ".join(cvx_nodes)}"')

    shell_script = "\n".join(sh) + "\n"

    with open(shell_path, "w") as f:
        f.write(shell_script)
    os.chmod(shell_path, 0o755)

    print(f"📄 FILE 3 — Shell script → {shell_filename}")
    print(f"{'─'*55}")
    print(shell_script)
    print(f"{'─'*55}")

    # ── File 4: docker cp copy script ────────────────────────────────────────
    copy_filename = base_name + "_copy_configs.sh"
    copy_path     = os.path.join(script_dir, copy_filename)

    cp = []
    cp.append("#!/bin/bash")
    cp.append("# Auto-generated: copy configs FROM running containers TO local config/ folder")
    cp.append(f"# Run AFTER: containerlab deploy -t {yaml_nobinds}")
    cp.append(f"# Run BEFORE: containerlab destroy -t {yaml_nobinds}")
    cp.append("")
    cp.append("set -e")
    cp.append("")

    for nname in cvx_nodes:
        container = f"clab-{lab_name}-{nname}"
        cp.append(f"# ── {nname}  (container: {container}) ──")
        cp.append(f"docker cp {container}:/etc/network/interfaces config/{nname}/interfaces")
        cp.append(f"docker cp {container}:/etc/frr/daemons        config/{nname}/daemons")
        cp.append(f"docker cp {container}:/etc/frr/frr.conf       config/{nname}/frr.conf")
        cp.append("")

    cp.append(f'echo "✅ Configs copied from containers for: {", ".join(cvx_nodes)}"')
    cp.append(f'echo "Now run: containerlab destroy -t {yaml_nobinds} && containerlab deploy -t {yaml_with}"')

    copy_script = "\n".join(cp) + "\n"

    with open(copy_path, "w") as f:
        f.write(copy_script)
    os.chmod(copy_path, 0o755)

    print(f"📄 FILE 4 — Copy config script → {copy_filename}")
    print(f"{'─'*55}")
    print(copy_script)
    print(f"{'─'*55}")

    print("\n✅  4 files generated!")
    print(f"   1️⃣  {yaml_with}           ← final deploy (with binds)")
    print(f"   2️⃣  {yaml_nobinds}    ← first deploy (no binds)")
    print(f"   3️⃣  {shell_filename}       ← create empty config folders/files")
    print(f"   4️⃣  {copy_filename}  ← copy configs from containers")
    print(f"\n🚀  Workflow:")
    print(f"   bash {shell_filename}")
    print(f"   containerlab deploy -t {yaml_nobinds}")
    print(f"   bash {copy_filename}")
    print(f"   containerlab destroy -t {yaml_nobinds}")
    print(f"   containerlab deploy -t {yaml_with}")

if __name__ == "__main__":
    main()
