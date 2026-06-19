from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    mcp_enabled = fields.Boolean(
        string="Enable MCP Access",
        help="Master switch to enable or disable all MCP server functionality. "
        "When disabled, all MCP endpoints (REST API and XML-RPC) will return "
        "errors and deny access to any MCP operations.",
        config_parameter="mcp_server.enabled",
        default=False,
    )
    mcp_request_limit = fields.Integer(
        string="Request Limit per Minute",
        help="Maximum number of API requests allowed per user per minute. "
        "Set to 0 to disable rate limiting and allow unlimited requests. "
        "This helps prevent API abuse and ensures fair usage across all users. "
        "Default: 300 requests/minute.",
        config_parameter="mcp_server.request_limit",
        default=300,
    )
    mcp_request_timeout = fields.Integer(
        string="Request Timeout (seconds)",
        help="Maximum time in seconds allowed for processing a single MCP request. "
        "Requests exceeding this limit will be terminated to prevent server overload. "
        "This protects against long-running queries and ensures system responsiveness. "
        "Default: 30 seconds.",
        config_parameter="mcp_server.request_timeout",
        default=30,
    )
    mcp_enable_logging = fields.Boolean(
        string="Enable Request Logging",
        help="When enabled, all MCP API requests and responses will be logged for "
        "auditing and debugging purposes. This includes request details, response "
        "times, and any errors. Useful for monitoring API usage and troubleshooting.",
        config_parameter="mcp_server.enable_logging",
        default=True,
    )
    mcp_enable_rate_limiting = fields.Boolean(
        string="Enable Rate Limiting",
        help="When enabled, enforces the request limit per minute for each user. "
        "Rate limiting helps prevent API abuse and ensures fair resource allocation. "
        "Configure the limit using the 'Request Limit per Minute' setting above.",
        config_parameter="mcp_server.enable_rate_limiting",
        default=False,
    )
    mcp_log_retention_days = fields.Integer(
        string="Log Retention (days)",
        help="Number of days to keep MCP log entries. Logs older than this will be "
        "automatically deleted to save storage space. Set to 0 to keep logs forever. "
        "Default: 30 days.",
        config_parameter="mcp_server.log_retention_days",
        default=30,
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        params = self.env["ir.config_parameter"].sudo()

        res.update(
            mcp_enabled=params.get_param("mcp_server.enabled", "False") == "True",
            mcp_request_limit=int(params.get_param("mcp_server.request_limit", "300")),
            mcp_request_timeout=int(
                params.get_param("mcp_server.request_timeout", "30")
            ),
            mcp_enable_logging=params.get_param("mcp_server.enable_logging", "True")
            == "True",
            mcp_enable_rate_limiting=params.get_param(
                "mcp_server.enable_rate_limiting", "False"
            )
            == "True",
            mcp_log_retention_days=int(
                params.get_param("mcp_server.log_retention_days", "30")
            ),
        )
        return res

    def set_values(self):
        result = super().set_values()
        params = self.env["ir.config_parameter"].sudo()

        params.set_param("mcp_server.enabled", str(self.mcp_enabled))
        params.set_param("mcp_server.request_limit", str(self.mcp_request_limit))
        params.set_param("mcp_server.request_timeout", str(self.mcp_request_timeout))
        params.set_param("mcp_server.enable_logging", str(self.mcp_enable_logging))
        params.set_param(
            "mcp_server.enable_rate_limiting", str(self.mcp_enable_rate_limiting)
        )
        params.set_param(
            "mcp_server.log_retention_days", str(self.mcp_log_retention_days)
        )

        return result
