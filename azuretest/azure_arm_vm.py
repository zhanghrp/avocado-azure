"""
Utility classes and functions to handle Virtual Machine, blob, container and
storage account using azure cli in arm mode.

:copyright: 2016 Red Hat Inc.
"""

import time
import string
import os
import logging
import fcntl
import re
import shutil
import tempfile
import platform

import aexpect
from avocado.utils import process
from avocado.utils import crypto
from avocado.core import exceptions

from . import azure_vm
from . import azure_cli_arm
from . import azure_cli_common
from . import remote
from . import data_dir
from . import utils_misc

class VMARM(azure_vm.BaseVM):

    """
    This class handles all basic VM operations for ARM.
    """

    def __init__(self, name, size, params):
        """
        Initialize the object and set a few attributes.

        :param name: The name of the object
        :param size: The VM size
        :param params: A dict containing VM params
                (see method make_create_command for a full description)
        """
        self.size = size
        self.mode = "ARM"
        super(VMARM, self).__init__(name, size, params)
        logging.info("Azure VM '%s'", self.name)

    def vm_create(self, options=''):
        """
        This helps to create a VM

        :param options: extra options
        :return: Zero if success to create VM
        """
        if not self.exists():
            return azure_cli_arm.vm_create(self.params, options).exit_status

    def vm_update(self, params):
        """
        This helps to update VM info

        :param params: A dict containing VM params
        """
        if params is None:
            self.params = azure_cli_arm.vm_show(self.params["name"]).stdout
        else:
            self.params = params

    def verify_alive(self):
        """
        Make sure the VM is alive.

        :raise VMDeadError: If the VM is dead
        """
        raise NotImplementedError

    def is_running(self):
        """
        Return True if VM is running.
        """
        raise NotImplementedError

    def is_stopped(self):
        """
        Return True if VM is stopped.
        """
        raise NotImplementedError

    def is_deallocated(self):
        """
        Return True if VM is deallocated.
        """
        raise NotImplementedError

    def exists(self):
        """
        Return True if VM exists.
        """
        ret = azure_cli_arm.vm_show(self.name)
        if not isinstance(ret.stdout, dict) and \
           ret.stdout.strip() == "No VMs found":
            return False
        else:
            return True

    def restart(self, timeout=azure_vm.BaseVM.RESTART_TIMEOUT):
        """
        Reboot the VM and wait for it to come back up by trying to log in until
        timeout expires.

        :param timeout: Time to wait for login to succeed (after rebooting).
        """
        return azure_cli_arm.vm_restart(self.name, timeout=timeout).exit_status

    def start(self):
        """
        Starts this VM.
        """
        return azure_cli_arm.vm_start(self.name).exit_status

    def shutdown(self):
        """
        Shuts down this VM.
        """
        return azure_cli_arm.vm_shutdown(self.name).exit_status

    def delete(self, timeout=azure_vm.BaseVM.DELETE_TIMEOUT):
        """
        Delete this VM.

        :param timeout: Time to wait for deleting the VM.
        """
        return azure_cli_arm.vm_delete(self.name, timeout=timeout).exit_status

    def capture(self, vm_image_name, cmd_params=None,
                timeout=azure_vm.BaseVM.DEFAULT_TIMEOUT):
        """
        Capture this VM.
        """
        return azure_cli_arm.vm_capture(self.name, vm_image_name, cmd_params,
                                        timeout=timeout).exit_status

    def get_public_address(self):
        """
        Get the public IP address

        :return:
        """
        return self.params("VirtualIPAddresses")[0]("address")

    def get_ssh_port(self):
        """
        Get the ssh port

        :return:
        """
        raise NotImplementedError

    def getenforce(self):
        """
        Set SELinux mode in the VM.

        :return: SELinux mode [Enforcing|Permissive|Disabled]
        """
        raise NotImplementedError

    def setenforce(self, mode):
        """
        Set SELinux mode in the VM.

        :param mode: SELinux mode [Enforcing|Permissive|1|0]
        """
        raise NotImplementedError
