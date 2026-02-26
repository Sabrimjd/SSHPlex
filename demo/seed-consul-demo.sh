#!/bin/sh
set -eu

CONSUL_URL="http://consul:8500"
DEMO_IP="192.168.31.216"

echo "Waiting for Consul API..."
until curl -fsS "$CONSUL_URL/v1/status/leader" >/dev/null; do
  sleep 1
done

register_node() {
  node_name="$1"
  cat <<EOF | curl -fsS -X PUT "$CONSUL_URL/v1/catalog/register" -H "Content-Type: application/json" -d @-
{
  "Node": "$node_name",
  "Address": "$DEMO_IP",
  "Datacenter": "dc1",
  "NodeMeta": {
    "cluster": "demo",
    "role": "ssh"
  }
}
EOF
}

register_node "demo-consul-app-01"
register_node "demo-consul-app-02"
register_node "demo-consul-db-01"

echo "Consul demo nodes registered: demo-consul-app-01, demo-consul-app-02, demo-consul-db-01"
