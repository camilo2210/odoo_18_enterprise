# MCP Server for Odoo

An Odoo module that enables Model Context Protocol (MCP) integration, allowing AI assistants to securely access and interact with your Odoo data. Supports full CRUD operations - create, read, update, and delete records through natural language.

## Features

- 🔐 **Secure API Access**: API key authentication with rate limiting
- 🎯 **Granular Permissions**: Control read/write/create/delete access per model
- 🌐 **REST & XML-RPC APIs**: Dual protocol support for maximum compatibility
- 👥 **Role-Based Access**: MCP Administrator and MCP User security groups
- 🖥️ **User-Friendly UI**: Integrated configuration in Odoo settings
- 📊 **Model Selection**: Easy-to-use wizard for enabling models
- 🔍 **Access Control**: Multi-layered security with Odoo's permission system

## What Can You Do With This Module?

This module opens up powerful AI-assisted workflows for your Odoo instance:

**Data Retrieval & Analysis:**
- **Customer Service Automation**: Let AI assistants look up customer orders, check inventory, and provide instant support
- **Sales Intelligence**: Query your CRM data naturally - "Show me all leads from Spain that haven't been contacted in 30 days"
- **Inventory Management**: Ask questions like "Which products are low in stock?" or "What were our top selling items last month?"
- **Financial Insights**: Get quick answers about invoices, payments, and financial status without complex reports
- **HR Queries**: Find employee information, leave balances, or department structures through natural language
- **Project Management**: Track project progress, find overdue tasks, or check team workloads conversationally

**Data Management & Automation:**
- **Contact Management**: Create new customers, update contact information, or manage supplier records
- **Product Catalog**: Add new products, update prices, or modify inventory levels
- **Order Processing**: Create sales orders, update order status, or manage deliveries
- **Task Creation**: Add new tasks to projects, assign team members, or update progress
- **Event Scheduling**: Create calendar events, schedule meetings, or manage appointments
- **Data Cleanup**: Remove test records, archive old data, or maintain data quality

## Requirements

To use this module, you need:

1. **This Odoo Module** - Provides the API endpoints and security layer
2. **MCP Server for Odoo** - The Python package that connects AI assistants to your Odoo instance

## Installation

### Step 1: Install from Odoo App Store

1. Download the module
2. Copy to Odoo addons
   ```bash
   cp -r mcp_server /path/to/odoo/addons/
   ```
3. Update the module list:
   - Navigate to Apps in Odoo
   - Click "Update Apps List"
   - Search for "MCP Server"
4. Click Install on the MCP Server module

### Step 2: Configure the Module

1. **Navigate to Settings**:
   - Go to Settings > MCP Server

2. **Enable Models**:
   - Click "Configure Models" or go to MCP Server > Enabled Models
   - Add models you want to expose (e.g., res.partner, product.product)
   - Set permissions for each model:
     - ✅ Can Read
     - ✅ Can Write
     - ✅ Can Create
     - ✅ Can Delete

3. **Generate API Keys**:
   - Go to Settings > Users & Companies > Users
   - Select a user
   - Navigate to the "API Keys" tab
   - Click "New API Key"
   - Provide a description and generate the key
   - **Important**: Save the key immediately, it won't be shown again

### Step 3: Install UV on Your Local Computer

The MCP server runs on your **local computer** (where Claude Desktop is installed), not on your Odoo server. First, install UV:

**On macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**On Windows:**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

After installation, restart your terminal.

### Step 4: Configure the MCP Client

The [MCP Server for Odoo](https://github.com/ivnvxd/mcp-server-odoo) Python package connects AI assistants to your Odoo instance. It supports both stdio (default) and streamable-http transports.

**Standard Configuration (stdio transport):**
Configure it in your AI assistant (e.g., Claude Desktop):
```json
{
  "mcpServers": {
    "odoo": {
      "command": "uvx",
      "args": ["mcp-server-odoo"],
      "env": {
        "ODOO_URL": "https://your-company.odoo.com",
        "ODOO_API_KEY": "your-api-key-from-step-2",
        "ODOO_DB": "your-database-name"
      }
    }
  }
}
```

**HTTP Transport Configuration:**
For web-based or remote MCP clients that need HTTP connectivity:
```json
{
  "mcpServers": {
    "odoo": {
      "command": "uvx",
      "args": ["mcp-server-odoo", "--transport", "streamable-http", "--port", "8000"],
      "env": {
        "ODOO_URL": "https://your-company.odoo.com",
        "ODOO_API_KEY": "your-api-key-from-step-2",
        "ODOO_DB": "your-database-name"
      }
    }
  }
}
```
Then connect your client to `http://localhost:8000/mcp/`

### Environment Variables

Configure these environment variables for the MCP client:

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `ODOO_URL` | Yes | Your Odoo instance URL | `https://mycompany.odoo.com` |
| `ODOO_API_KEY` | Yes* | API key from Step 2 | `0ef5b399e9ee9c11b053dfb6...` |
| `ODOO_USER` | Yes* | Username (if not using API key) | `admin@mycompany.com` |
| `ODOO_PASSWORD` | Yes* | Password (if not using API key) | `your-password` |
| `ODOO_DB` | No | Database name (auto-detected if omitted) | `mycompany` |

*Use either `ODOO_API_KEY` or both `ODOO_USER` and `ODOO_PASSWORD`

### Security Groups

The module creates two security groups:

- **MCP Administrator**: Can configure MCP settings and manage enabled models
- **MCP User**: Can access MCP-enabled models based on configured permissions

Assign users to appropriate groups in Settings > Users & Companies > Users.

## API Endpoints

### REST API

All REST endpoints require API key authentication via `X-API-Key` header.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp/health` | GET | Health check (no auth required) |
| `/mcp/system/info` | GET | Get database and server information |
| `/mcp/auth/validate` | POST | Validate API key |
| `/mcp/models` | GET | List all MCP-enabled models |
| `/mcp/models/{model}/access` | GET | Check access permissions for a model |

### XML-RPC API

MCP-specific XML-RPC endpoints with enhanced access control:

| Endpoint | Description |
|----------|-------------|
| `/mcp/xmlrpc/common` | Authentication services |
| `/mcp/xmlrpc/db` | Database operations |
| `/mcp/xmlrpc/object` | Model operations with MCP access control |

## Usage Example

### Testing the Installation

1. **Check health endpoint**:
   ```bash
   curl https://your-odoo.com/mcp/health
   ```

2. **Validate API key**:
   ```bash
   curl -X POST https://your-odoo.com/mcp/auth/validate \
     -H "X-API-Key: your-api-key-here" \
     -H "Content-Type: application/json"
   ```

3. **List enabled models**:
   ```bash
   curl https://your-odoo.com/mcp/models \
     -H "X-API-Key: your-api-key-here"
   ```


## Security Considerations

- **API Key Security**: Keep API keys secure and rotate them regularly
- **Model Access**: Only enable models that are necessary for your use case
- **Permissions**: Follow the principle of least privilege
- **HTTPS**: Always use HTTPS in production environments
- **Rate Limiting**: The module includes rate limiting for API endpoints
- **Audit Trail**: All MCP operations are logged for security auditing

## Development

### Running Tests

```bash
# Run all MCP module tests
/path/to/odoo-bin \
  --test-enable \
  --test-tags=mcp_server \
  --stop-after-init \
  -d your_database

# Test API endpoints
bash tests/test_mcp_endpoints.sh

# Debug mode
DEBUG=true bash tests/test_mcp_endpoints.sh
```

## Troubleshooting

<details>
<summary>Module Not Found</summary>

- Ensure the module is in the correct addons path
- Update the apps list in Odoo (Apps > Update Apps List)
- Check module dependencies are satisfied
- Verify the module manifest file is valid
</details>

<details>
<summary>API Key Not Working</summary>

- Verify the key is active in the user's API Keys tab
- Check the user has appropriate MCP permissions (MCP User or MCP Administrator group)
- Ensure the X-API-Key header is properly formatted
- Try regenerating the API key
- Check that the user account is active and not archived
</details>

<details>
<summary>Model Access Denied</summary>

- Confirm the model is in the MCP enabled models list (Settings > MCP Server > Enabled Models)
- Check the specific permissions (read/write/create/delete) for that model
- Verify the user's security group membership
- Ensure the user has Odoo permissions for that model too
- Check if record rules are blocking access
</details>

<details>
<summary>Connection Issues</summary>

- Verify your Odoo URL is accessible from the client
- Check if HTTPS is properly configured
- Ensure firewall rules allow the connection
- Test with the health endpoint first: `curl https://your-odoo.com/mcp/health`
- Check Odoo logs for any error messages
</details>

<details>
<summary>Performance Issues</summary>

- Enable only necessary models to reduce overhead
- Use field filtering in API calls to limit data transfer
- Consider implementing caching in your client
- Check if rate limiting is affecting your requests
- Monitor Odoo server resources (CPU, memory, database)
</details>

<details>
<summary>MCP Client "spawn uvx ENOENT" Error</summary>

This error means UV is not installed on your local computer:

**Quick Fix:**
1. Install UV on your local machine (see Step 3 above)
2. Restart your terminal and Claude Desktop
3. If on macOS and still having issues, launch Claude from Terminal:
   ```bash
   open -a "Claude"
   ```

**Alternative:** Use the full path to uvx in your configuration (run `which uvx` to find it)
</details>

## License

This module is licensed under the [GNU Lesser General Public License v3.0 (LGPL-3)](https://www.gnu.org/licenses/lgpl-3.0.html). See [LICENSE](LICENSE) for the full text.

## Acknowledgments

This module is part of the [Odoo MCP Server](https://github.com/ivnvxd/mcp-server-odoo) project, enabling AI assistants to work with Odoo data through the Model Context Protocol.
