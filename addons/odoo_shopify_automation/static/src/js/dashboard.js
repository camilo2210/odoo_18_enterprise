/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, onWillStart, useState } from "@odoo/owl";

class ShopifyDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: false,
            realTimeData: {},
            chartData: {},
            notifications: [],
            systemHealth: {},
        });
        
        this.chartInstances = new Map();
        this.updateInterval = null;
    }

    async onWillStart() {
        await this.loadDashboardData();
        this.initializeRealTimeUpdates();
    }

    onMounted() {
        this.initializeCharts();
        this.setupEventListeners();
    }

    async loadDashboardData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "shopify.instance",
                "get_dashboard_data",
                []
            );
            
            this.state.realTimeData = data;
            this.updateCharts(data);
        } catch (error) {
            console.error("Failed to load dashboard data:", error);
            this.notification.add("Failed to load dashboard data", {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    initializeRealTimeUpdates() {
        // Update data every 30 seconds
        this.updateInterval = setInterval(() => {
            this.loadDashboardData();
        }, 30000);

        // Setup WebSocket connection for real-time updates
        this.setupWebSocket();
    }

    setupWebSocket() {
        // WebSocket connection for real-time updates
        const ws = new WebSocket(`ws://${window.location.host}/shopify/ws`);
        
        ws.onopen = () => {
            console.log("WebSocket connected for real-time updates");
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleRealTimeUpdate(data);
        };
        
        ws.onerror = (error) => {
            console.error("WebSocket error:", error);
        };
        
        ws.onclose = () => {
            console.log("WebSocket disconnected, attempting to reconnect...");
            setTimeout(() => this.setupWebSocket(), 5000);
        };
    }

    handleRealTimeUpdate(data) {
        switch (data.type) {
            case 'order_created':
                this.handleOrderCreated(data.payload);
                break;
            case 'product_updated':
                this.handleProductUpdated(data.payload);
                break;
            case 'customer_synced':
                this.handleCustomerSynced(data.payload);
                break;
            case 'error_occurred':
                this.handleErrorOccurred(data.payload);
                break;
            case 'system_health':
                this.handleSystemHealthUpdate(data.payload);
                break;
        }
    }

    handleOrderCreated(orderData) {
        // Update order count
        this.state.realTimeData.order_count++;
        
        // Add notification
        this.addNotification({
            type: 'success',
            title: 'New Order',
            message: `Order #${orderData.order_number} created`,
            icon: 'fa-shopping-cart'
        });
        
        // Update charts
        this.updateSalesChart(orderData);
    }

    handleProductUpdated(productData) {
        // Add notification
        this.addNotification({
            type: 'info',
            title: 'Product Updated',
            message: `Product "${productData.name}" updated`,
            icon: 'fa-cube'
        });
    }

    handleCustomerSynced(customerData) {
        // Update customer count
        this.state.realTimeData.customer_count++;
        
        // Add notification
        this.addNotification({
            type: 'success',
            title: 'Customer Synced',
            message: `Customer "${customerData.name}" synced`,
            icon: 'fa-users'
        });
    }

    handleErrorOccurred(errorData) {
        // Update error count
        this.state.realTimeData.error_count++;
        
        // Add notification
        this.addNotification({
            type: 'danger',
            title: 'Error Occurred',
            message: errorData.message,
            icon: 'fa-exclamation-triangle'
        });
    }

    handleSystemHealthUpdate(healthData) {
        this.state.systemHealth = healthData;
        this.updateSystemHealthDisplay();
    }

    addNotification(notification) {
        this.state.notifications.unshift({
            ...notification,
            id: Date.now(),
            timestamp: new Date()
        });
        
        // Remove old notifications (keep only last 10)
        if (this.state.notifications.length > 10) {
            this.state.notifications = this.state.notifications.slice(0, 10);
        }
        
        // Auto-remove notification after 5 seconds
        setTimeout(() => {
            this.removeNotification(notification.id);
        }, 5000);
    }

    removeNotification(notificationId) {
        const index = this.state.notifications.findIndex(n => n.id === notificationId);
        if (index > -1) {
            this.state.notifications.splice(index, 1);
        }
    }

    initializeCharts() {
        // Initialize Chart.js charts
        this.initializeSalesChart();
        this.initializeRevenueChart();
        this.initializeCustomerChart();
        this.initializeInventoryChart();
    }

    initializeSalesChart() {
        const ctx = document.getElementById('sales_chart');
        if (!ctx) return;

        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Sales',
                    data: [],
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });

        this.chartInstances.set('sales', chart);
    }

    initializeRevenueChart() {
        const ctx = document.getElementById('revenue_chart');
        if (!ctx) return;

        const chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Online Sales', 'In-Store Sales', 'Wholesale'],
                datasets: [{
                    data: [65, 25, 10],
                    backgroundColor: [
                        '#667eea',
                        '#764ba2',
                        '#f093fb'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });

        this.chartInstances.set('revenue', chart);
    }

    initializeCustomerChart() {
        const ctx = document.getElementById('customer_chart');
        if (!ctx) return;

        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    label: 'New Customers',
                    data: [120, 150, 180, 200, 220, 250],
                    backgroundColor: '#8b5cf6',
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });

        this.chartInstances.set('customer', chart);
    }

    initializeInventoryChart() {
        const ctx = document.getElementById('inventory_chart');
        if (!ctx) return;

        const chart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: ['In Stock', 'Low Stock', 'Out of Stock'],
                datasets: [{
                    data: [70, 20, 10],
                    backgroundColor: [
                        '#10b981',
                        '#f59e0b',
                        '#ef4444'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });

        this.chartInstances.set('inventory', chart);
    }

    updateCharts(data) {
        // Update sales chart
        const salesChart = this.chartInstances.get('sales');
        if (salesChart && data.sales_chart_data) {
            salesChart.data.labels = data.sales_chart_data.labels;
            salesChart.data.datasets[0].data = data.sales_chart_data.values;
            salesChart.update('none');
        }

        // Update other charts with real-time data
        this.updateRevenueChart(data);
        this.updateCustomerChart(data);
        this.updateInventoryChart(data);
    }

    updateSalesChart(orderData) {
        const salesChart = this.chartInstances.get('sales');
        if (salesChart) {
            // Add new data point
            const now = new Date();
            const timeLabel = now.toLocaleTimeString();
            
            salesChart.data.labels.push(timeLabel);
            salesChart.data.datasets[0].data.push(orderData.amount);
            
            // Keep only last 20 data points
            if (salesChart.data.labels.length > 20) {
                salesChart.data.labels.shift();
                salesChart.data.datasets[0].data.shift();
            }
            
            salesChart.update('none');
        }
    }

    updateRevenueChart(data) {
        const revenueChart = this.chartInstances.get('revenue');
        if (revenueChart && data.revenue_distribution) {
            revenueChart.data.datasets[0].data = data.revenue_distribution;
            revenueChart.update('none');
        }
    }

    updateCustomerChart(data) {
        const customerChart = this.chartInstances.get('customer');
        if (customerChart && data.customer_growth) {
            customerChart.data.datasets[0].data = data.customer_growth;
            customerChart.update('none');
        }
    }

    updateInventoryChart(data) {
        const inventoryChart = this.chartInstances.get('inventory');
        if (inventoryChart && data.inventory_status) {
            inventoryChart.data.datasets[0].data = data.inventory_status;
            inventoryChart.update('none');
        }
    }

    updateSystemHealthDisplay() {
        const healthElements = document.querySelectorAll('.o_health_value');
        healthElements.forEach(element => {
            const metric = element.dataset.metric;
            const value = this.state.systemHealth[metric];
            
            if (value !== undefined) {
                element.textContent = value;
                
                // Update color based on health status
                element.className = 'o_health_value';
                if (value > 90) {
                    element.classList.add('o_health_good');
                } else if (value > 70) {
                    element.classList.add('o_health_warning');
                } else {
                    element.classList.add('o_health_error');
                }
            }
        });
    }

    setupEventListeners() {
        // KPI card click events
        document.querySelectorAll('.o_kpi_card').forEach(card => {
            card.addEventListener('click', (e) => {
                this.handleKPIClick(e.currentTarget);
            });
        });

        // Quick action button events
        document.querySelectorAll('.o_action_card').forEach(button => {
            button.addEventListener('click', (e) => {
                this.handleQuickAction(e.currentTarget);
            });
        });

        // Notification close events
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('o_notification_close')) {
                const notificationId = parseInt(e.target.dataset.notificationId);
                this.removeNotification(notificationId);
            }
        });
    }

    handleKPIClick(card) {
        const cardType = card.classList.contains('o_kpi_sales') ? 'sales' :
                        card.classList.contains('o_kpi_orders') ? 'orders' :
                        card.classList.contains('o_kpi_customers') ? 'customers' :
                        card.classList.contains('o_kpi_products') ? 'products' :
                        card.classList.contains('o_kpi_queue') ? 'queue' : 'errors';

        // Navigate to detailed view
        this.navigateToDetailView(cardType);
    }

    handleQuickAction(button) {
        const action = button.dataset.action;
        
        switch (action) {
            case 'orders':
                this.navigateToOrders();
                break;
            case 'products':
                this.navigateToProducts();
                break;
            case 'customers':
                this.navigateToCustomers();
                break;
            case 'queue':
                this.navigateToQueue();
                break;
            case 'logs':
                this.navigateToLogs();
                break;
            case 'cron':
                this.navigateToCron();
                break;
        }
    }

    navigateToDetailView(type) {
        // Navigate to detailed analytics view
        const action = {
            type: 'ir.actions.act_window',
            res_model: 'shopify.analytics',
            view_mode: 'form',
            target: 'current',
            context: {
                'default_analytics_type': type,
                'default_date_from': this.state.realTimeData.date_from,
                'default_date_to': this.state.realTimeData.date_to
            }
        };
        
        this.env.services.action.doAction(action);
    }

    navigateToOrders() {
        this.env.services.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'shopify.order',
            view_mode: 'list,form',
            target: 'current'
        });
    }

    navigateToProducts() {
        this.env.services.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'shopify.product',
            view_mode: 'list,form',
            target: 'current'
        });
    }

    navigateToCustomers() {
        this.env.services.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'shopify.customer',
            view_mode: 'list,form',
            target: 'current'
        });
    }

    navigateToQueue() {
        this.env.services.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'shopify.queue.job',
            view_mode: 'list,form',
            target: 'current'
        });
    }

    navigateToLogs() {
        this.env.services.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'shopify.log',
            view_mode: 'list,form',
            target: 'current'
        });
    }

    navigateToCron() {
        this.env.services.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'shopify.cron',
            view_mode: 'list,form',
            target: 'current'
        });
    }

    // Cleanup on component destruction
    willUnmount() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        
        // Destroy chart instances
        this.chartInstances.forEach(chart => {
            chart.destroy();
        });
        this.chartInstances.clear();
    }
}

// Register the component
registry.category("actions").add("shopify_dashboard", ShopifyDashboard);

export default ShopifyDashboard; 