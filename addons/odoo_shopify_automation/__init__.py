# -*- coding: utf-8 -*-

from . import models
from . import wizard
from . import controllers


def post_init_hook(env):
    """
    Post-installation hook for Shopify automation module.
    This function is called after the module is installed.
    """
    # Initialize default settings if needed
    # Create default cron jobs if they don't exist
    # Set up default webhook configurations
    pass


def uninstall_hook(env):
    """
    Uninstallation hook for Shopify automation module.
    This function is called when the module is uninstalled.
    """
    # Clean up any module-specific data
    # Remove cron jobs created by this module
    # Clean up webhook configurations
    pass 