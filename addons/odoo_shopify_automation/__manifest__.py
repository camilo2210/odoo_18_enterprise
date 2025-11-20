{
    'name': 'Odoo Shopify Connector PRO - Advanced Automation Suite',
    'version': '18.0.2.0.0',
    'summary': 'Enterprise-Grade Shopify-Odoo Integration with Advanced Automation & Analytics',
    'description': '''
🚀 **ENTERPRISE-GRADE SHOPIFY INTEGRATION SUITE**

🔗 **Core Integration Features:**
• Multi-store Shopify integration with advanced connection management
• Bidirectional real-time synchronization (Odoo ↔ Shopify)
• Advanced webhook management with custom endpoints
• Multi-location inventory support with location mapping
• Product variants, images, and SEO optimization
• Advanced order workflow with custom status mapping

⚙️ **Advanced Automation & AI:**
• AI-powered order risk assessment and fraud detection
• Smart inventory forecasting and reorder automation
• Automated customer segmentation and marketing
• Intelligent product recommendation engine
• Advanced cron job management with custom scheduling
• Queue management with priority-based processing

💰 **Financial & Analytics Suite:**
• Comprehensive payout reports and reconciliation
• Advanced financial analytics with profit margin tracking
• Multi-currency support with real-time exchange rates
• Tax calculation and compliance management
• Advanced reporting with custom dashboards
• Performance metrics and KPI tracking

📊 **Modern Analytics Dashboard:**
• Real-time sales analytics with interactive charts
• Customer behavior analysis and insights
• Product performance tracking and optimization
• Inventory turnover and stock level monitoring
• Revenue forecasting and trend analysis
• Custom report builder with drag-and-drop interface

🛡️ **Security & Compliance:**
• Role-based access control with granular permissions
• Multi-company support with data isolation
• GDPR compliance and data protection
• Audit trail and activity logging
• Secure API credential management
• Two-factor authentication support

🚚 **Advanced Shipping & Fulfillment:**
• 100+ carrier integration with real-time tracking
• Automated shipping label generation
• Multi-warehouse fulfillment optimization
• Returns management and processing
• International shipping compliance
• Delivery time optimization

🎨 **Modern UI/UX Design:**
• Responsive design with mobile optimization
• Dark/Light theme support
• Customizable dashboard layouts
• Advanced search and filtering
• Drag-and-drop interface elements
• Real-time notifications and alerts

🔧 **Developer & Admin Features:**
• RESTful API for custom integrations
• Webhook testing and debugging tools
• Performance monitoring and optimization
• Backup and restore functionality
• Migration tools for data import/export
• Extensive logging and error tracking

Perfect for enterprise e-commerce businesses requiring the most advanced Shopify-Odoo integration with cutting-edge features and modern design.

Developed by ECOSIRE (PRIVATE) LIMITED - Enterprise Solutions Division.
    ''',
    'author': 'ECOSIRE (PRIVATE) LIMITED',
    'website': 'https://www.ecosire.com/',
    'category': 'Connector',
    'depends': [
        'base', 
        'sale_management', 
        'stock', 
        'account', 
        'delivery', 
        'mail', 
        'web', 
        'portal',
        'product',
        'purchase',
        'hr',
        'contacts',
        'website',
        'payment'
    ],
    'data': [
        # Security - Groups must be loaded before access rights
        'security/security.xml',
        'security/record_rules.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/ir_cron_data.xml',
        'data/ir_sequence_data.xml',
        
        # Views - Individual model views must be loaded before dashboard to define actions
        'views/shopify_instance_view.xml',
        'views/shopify_product_view.xml',
        'views/shopify_order_view.xml',
        'views/shopify_customer_view.xml',
        'views/shopify_queue_job_view.xml',
        'views/shopify_log_view.xml',
        'views/shopify_cron_view.xml',
        'views/shopify_webhook_view.xml',
        'views/dashboard_view.xml',
        
        # Wizards - Must be loaded before menu to define actions
        'wizard/manual_sync_wizard_view.xml',
        
        # Menu - Must be loaded last to reference all actions
        'views/menu.xml',
    ],
    'images': [
        'static/description/cover.png',
        'static/description/Screen 1.png',
        'static/description/Screen 2.png',
        'static/description/Screen 3.png',
        'static/description/Screen 4.png',
        'static/description/Screen 5.png',
        'static/description/Screen 6.png',
        'static/description/Screen 7.png',
        'static/description/Screen 8.png',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'odoo_shopify_automation/static/src/css/dashboard.css',
            'odoo_shopify_automation/static/src/js/dashboard.js',
            'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.min.js',
            'https://cdn.jsdelivr.net/npm/apexcharts@3.45.0/dist/apexcharts.min.js',
            'https://cdn.jsdelivr.net/npm/apexcharts@3.45.0/dist/apexcharts.css',
        ],
    },
    'support': 'https://www.ecosire.com/support',
    'maintainer': 'ECOSIRE (PRIVATE) LIMITED',
    'price': 0.0,
    'currency': 'EUR',
    'external_dependencies': {
        'python': [
            'ShopifyAPI',
            'requests',
            'python-dateutil',
            'pandas',
            'numpy',
        ],
    },
    'demo': [
        'demo/shopify_demo.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
} 