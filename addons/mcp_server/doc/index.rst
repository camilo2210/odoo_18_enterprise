MCP Server for Odoo
===================================

Overview
--------

The MCP Server module enables AI assistants to securely access and interact with your Odoo data through the Model Context Protocol (MCP). This module provides the server-side infrastructure within Odoo, while a separate Python package handles the MCP client communication. Supports full CRUD operations - create, read, update, and delete records through natural language.

Installation
------------

1. Download and install the module in your Odoo instance
2. Navigate to Settings > MCP Server to configure access
3. Install UV on your local computer (where your AI assistant runs):

   **macOS/Linux:**

   .. code-block:: bash

      curl -LsSf https://astral.sh/uv/install.sh | sh

   **Windows:**

   .. code-block:: powershell

      powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

   After installation, restart your terminal.

4. Configure your AI assistant to connect via MCP using the companion Python package

Configuration
-------------

Model Access
~~~~~~~~~~~~

1. Go to Settings > MCP Server > Enabled Models
2. Add models you want to expose (e.g., res.partner, product.product)
3. Configure permissions for each model:
   - Read access
   - Write access
   - Create access
   - Delete access

API Key Setup
~~~~~~~~~~~~~

1. Navigate to Settings > Users & Companies > Users
2. Select the user for MCP access
3. Go to API Keys tab
4. Generate a new API key with appropriate scope
5. Use this key in your MCP client configuration

Client Setup
~~~~~~~~~~~~

.. important::
   The MCP Server runs on your **local computer** (where Claude Desktop or other AI assistants are installed),
   not on the Odoo server. The Python package connects from your local machine to your remote Odoo instance.

After installing the module and generating an API key, you can configure your AI assistant using either transport method:

**Transport Options**

The MCP server supports two transport types:

- **stdio transport** (default): For local AI assistants like Claude Desktop, VS Code extensions
- **streamable-http transport**: For web-based clients or remote connections

**Standard Configuration (stdio transport):**

.. code-block:: json

   {
     "mcpServers": {
       "odoo": {
         "command": "uvx",
         "args": ["mcp-server-odoo"],
         "env": {
           "ODOO_URL": "https://your-odoo-instance.com",
           "ODOO_API_KEY": "your-api-key-here"
         }
       }
     }
   }

**HTTP Transport Configuration:**

For web-based or remote MCP clients:

.. code-block:: json

   {
     "mcpServers": {
       "odoo": {
         "command": "uvx",
         "args": ["mcp-server-odoo", "--transport", "streamable-http", "--port", "8000"],
         "env": {
           "ODOO_URL": "https://your-odoo-instance.com",
           "ODOO_API_KEY": "your-api-key-here"
         }
       }
     }
   }

Then connect your client to ``http://localhost:8000/mcp/``

**Client-Specific Examples**

**Claude Desktop**

Add to ``~/Library/Application Support/Claude/claude_desktop_config.json`` using the configuration examples above.

**Cursor**

Add to ``~/.cursor/mcp_settings.json`` using the configuration examples above.

**Claude Code**

Run the following command to add the Odoo MCP server:

.. code-block:: bash

   claude mcp add odoo \
     -e ODOO_URL=https://your-odoo-instance.com \
     -e ODOO_API_KEY=your-api-key-here \
     -- uvx ivnvxd/mcp-server-odoo

**Environment Variables**

The MCP client requires one of the following authentication methods:

**API Key Authentication (Recommended):**

- ``ODOO_URL``: Your Odoo instance URL (e.g., ``https://mycompany.odoo.com``)
- ``ODOO_API_KEY``: The API key generated in the previous step

**Username/Password Authentication:**

- ``ODOO_URL``: Your Odoo instance URL (e.g., ``https://mycompany.odoo.com``)
- ``ODOO_USER``: Your Odoo username
- ``ODOO_PASSWORD``: Your Odoo password

**Optional Variables:**

- ``ODOO_DB``: Database name (auto-detected if not specified)

Security Groups
~~~~~~~~~~~~~~~

The module creates two security groups:

- **MCP Administrator**: Can configure MCP settings and manage enabled models
- **MCP User**: Can access MCP-enabled models based on configured permissions

Usage Examples
--------------

Once configured, you can query and manage your Odoo data using natural language:

**Data Retrieval:**

- "Show me all customers from Spain"
- "Find products with stock below 10 units"
- "List today's sales orders over $1000"
- "Search for unpaid invoices from last month"

**Data Management:**

- "Create a new customer contact for Acme Corporation"
- "Add a new product called 'Premium Widget' with price $99.99"
- "Update the phone number for customer John Doe"
- "Change the status of order SO/2024/001 to confirmed"
- "Delete the test contact we created earlier"

API Endpoints
-------------

The module provides several REST and XML-RPC endpoints:

REST API
~~~~~~~~

- ``/mcp/health`` - Health check
- ``/mcp/system/info`` - System information
- ``/mcp/auth/validate`` - API key validation
- ``/mcp/models`` - List enabled models
- ``/mcp/models/{model}/access`` - Check model permissions

XML-RPC API
~~~~~~~~~~~

- ``/mcp/xmlrpc/common`` - Authentication
- ``/mcp/xmlrpc/db`` - Database operations
- ``/mcp/xmlrpc/object`` - Model operations

Security Considerations
-----------------------

- Use HTTPS in production environments
- Generate unique API keys for each integration
- Configure model access carefully - only enable necessary models
- Regularly review audit logs for suspicious activity
- Keep the module updated

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Module Not Installing**
- Check that all dependencies are satisfied
- Ensure Odoo 18.0 is being used

**API Key Not Working**
- Verify the key is active in user settings
- Check user has appropriate MCP permissions
- Ensure correct API key scope

**Model Access Denied**
- Confirm model is in enabled models list
- Check operation permissions for the model
- Verify user's security group membership

**"spawn uvx ENOENT" Error**

This error means UV is not installed on your local computer:

1. Install UV using the commands in the Installation section above
2. Restart your terminal and Claude Desktop
3. On macOS, if the issue persists, launch Claude from Terminal:

   .. code-block:: bash

      open -a "Claude"

4. Alternative: Use the full path to uvx (find it with ``which uvx``)

**Database Access Denied**

If you see "Access Denied" when the MCP server tries to list databases:

- This is normal security behavior on some Odoo instances
- You must specify the ``ODOO_DB`` environment variable in your configuration
- The server will use your specified database without validation

Support
-------

For support, reach out to product@erp.muchconsulting.de
