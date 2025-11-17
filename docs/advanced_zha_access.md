# Advanced ZHA Cluster Access

Compatibility: Home Assistant 2024.1+ (Python 3.11+)

Docs: [index](index.md) · [user guide](README.md)

For advanced users who want to directly access manufacturer attributes via ZHA developer tools.

Caution: Direct cluster operations bypass the integration’s safeguards (timeouts, retries, readback verification). Use with care.

Example: Read total steps (J1)

```yaml
service: zha.issue_zigbee_cluster_command
data:
  ieee: "00:12:4b:00:1c:a1:b2:c3"
  endpoint_id: 2
  cluster_id: 0x0102
  cluster_type: in
  command: read_attributes
  command_type: client
  args:
    attribute: 0x1002
  manufacturer: 0x10F2
```

Prefer the integration’s services where possible; they handle verification and error scenarios gracefully.
