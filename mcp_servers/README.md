# MCP Servers

RetailPulse AI uses the **official MongoDB MCP Server** as its partner integration.

## MongoDB MCP Server

**Package**: `mongodb-mcp-server` (npm)  
**Version**: Latest (pre-installed in Docker image)  
**Protocol**: Model Context Protocol (MCP) over stdio  

### Tools Exposed (20+)

| Tool | Operation | Used By |
|------|-----------|---------|
| `find` | Query documents | All agents |
| `aggregate` | Aggregation pipelines | Analytics, Anomaly |
| `insert-many` | Write documents | Advisor, Notification, Anomaly |
| `update-many` | Modify documents | Advisor |
| `collection-schema` | Inspect schema | Orchestrator |
| `db-stats` | Database statistics | Orchestrator |
| `atlas-get-performance-advisor` | Atlas recommendations | Orchestrator |
| `create-index` | Index management | Orchestrator |
| `list-collections` | List collections | All agents |

### How It's Wired

Each agent spawns the MCP server as a subprocess via `npx`:

```python
McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",
            args=["-y", "mongodb-mcp-server"],
            env={"MDB_MCP_CONNECTION_STRING": MONGODB_URI},
        ),
        timeout=60,
    ),
)
```

### Running Locally

```bash
# Test the MCP server directly
npx -y mongodb-mcp-server --help

# With a connection string
MDB_MCP_CONNECTION_STRING="mongodb+srv://..." npx -y mongodb-mcp-server
```

### Atlas API (Optional)

Set these env vars to enable Atlas management tools:
```
MDB_ATLAS_CLIENT_ID=your_client_id
MDB_ATLAS_CLIENT_SECRET=your_client_secret
```

This enables: `atlas-list-clusters`, `atlas-get-performance-advisor`,
`atlas-create-access-list`, `atlas-list-alerts`
