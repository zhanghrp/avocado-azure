"""
Wrappers for the Azure cli functions in both arm and asm mode.

:copyright: 2016 Red Hat Inc.
"""

import logging
import pexpect
import subprocess
import shlex


def login_azure(username, password):
    """
    This helps to login azure

    :param username: Azure subscription username
    :param password: Azure subscription password
    :return: True if operate successfully
    """
    cmd = "azure login -u %s" % username
    logging.debug("Login Azure with: %s", username)
    login_handle = pexpect.spawn(cmd)
    index = login_handle.expect(["[pP]assword:", pexpect.EOF, pexpect.TIMEOUT])
    if index == 0:
        logging.debug("Enter the password")
        login_handle.sendline(password)
        login_handle.sendline("\r")
        login_handle.expect(["[$#>]", pexpect.EOF, pexpect.TIMEOUT])
    else:
        return False
    logging.debug("Login successfully with: %s", username)
    return True


def logout_azure(username):
    """
    This helps to login azure

    :param username: Azure subscription username
    :return: True if operate successfully
    """
    cmd = "azure logout -u %s" % username
    logging.debug("Logout Azure with: %s", username)
    cmd = shlex.split(cmd)
    try:
        subprocess.check_call(cmd)
    except:
        logging.error("Failed to logout with: %s", username)
        raise
    logging.debug("Logout successfully with: %s", username)
    return True


def account_clear(options=''):
    """
    Remove a subscription or environment, or clear all of the stored account
    and environment info

    :return: True if operate successfully
    """
    cmd = "azure account clear --quiet %s" % options
    logging.debug("Clear Azure account")
    cmd = shlex.split(cmd)
    try:
        subprocess.check_call(cmd)
    except:
        logging.error("Failed to clear account")
        raise


def set_config_mode(mode="asm"):
    """
    Set the config mode

    :param mode: The mode will be set
    :return: True if operate successfully
    """
    logging.debug("Change the azure config mode as %s", mode)
    cmd = "azure config mode %s" % mode
    cmd = shlex.split(cmd)
    try:
        subprocess.check_call(cmd)
    except:
        logging.error("Fails to change the azure config mode: %s", mode)
        raise
    else:
        logging.debug("Success to change the azure config mode: %s", mode)
        return True
