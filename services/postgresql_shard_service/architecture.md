# PostgreSQL Sharded Cluster Architecture

- **Sharding**: 10+ shards with hash/range (PostgreSQL), 16384 slots + CRC16 (Redis),
  or vector distribution with consistent hashing (Qdrant).
- **Routing**: Key/vector routing to the correct shard and node.
- **Rebalancing**: Redistribute slots, key ranges or virtual nodes.
- **Replication**: 1 primary + N replicas per shard.
- **High Availability**: Patroni (PostgreSQL), Sentinel (Redis) or Raft (Qdrant).
- **Failover**: Automatic replica promotion.
- **Cross-shard query**: Scatter/gather across shards.
- **Monitoring**: Prometheus metrics endpoint.
- **Backup/Restore**: Metadata snapshots.
