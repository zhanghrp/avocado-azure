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
from . import azure_cli_asm
from . import azure_cli_common
from . import remote
from . import data_dir
from . import utils_misc

class VMASM(azure_vm.BaseVM):

    """
    This class handles all basic VM operations for ASM.
    """

    def __init__(self, name, size, params):
        """
        Initialize the object and set a few attributes.

        :param name: The name of the object
        :param size: The VM size
        :param params: A dict containing VM params
        params sample:
        {
          "DNSName": "wala680414cli...",
          "Location": "East US",
          "VMName": "wala680414cli",
          "IPAddress": "10.82.26.69",
          "InstanceStatus": "ReadyRole",
          "InstanceSize": "Medium",
          "Image": "wala68-20160414",
          "OSDisk": {
            "hostCaching": "ReadWrite",
            "name": "wala680414cli...",
            "mediaLink": "https://wala.blob.core.windows.net/.",
            "sourceImageName": "wala68-20160414",
            "operatingSystem": "Linux",
            "iOType": "Standard"
          },
          "DataDisks": [
            {
              "hostCaching": "None",
              "name": "wala680414cli...",
              "logicalDiskSizeInGB": 50,
              "mediaLink": "https://wala.blob.core.windows.net/...",
              "iOType": "Standard"
            },
            {
              "hostCaching": "ReadOnly",
              "name": "wala680414cli...",
              "logicalUnitNumber": 1,
              "logicalDiskSizeInGB": 100,
              "mediaLink": "https://wala.blob.core.windows.net/...",
              "iOType": "Standard"
            },
            {
              "hostCaching": "ReadWrite",
              "name": "wala680414cli...",
              "logicalUnitNumber": 2,
              "logicalDiskSizeInGB": 1023,
              "mediaLink": "https://wala.blob.core.windows.net/...",
              "iOType": "Standard"
            }
          ],
          "ReservedIPName": "",
          "VirtualIPAddresses": [
            {
              "address": "13",
              "name": "wala",
              "isDnsProgrammed": true
            }
          ],
          "PublicIPs": [],
          "Network": {
            "Endpoints": [
              {
                "localPort": 22,
                "name": "ssh",
                "port": 22,
                "protocol": "tcp",
                "virtualIPAddress": "13",
                "enableDirectServerReturn": false
              }
            ],
            "PublicIPs": [],
            "NetworkInterfaces": []
          }
        }
        """
        self.size = size
        self.mode = "ASM"
        super(VMASM, self).__init__(name, size, params)
        logging.info("Azure VM '%s'", self.name)

    def vm_create(self, options=''):
        """
        This helps to create a VM

        :param options: extra options
        :return: Zero if success to create VM
        """
        if not self.exists():
            return azure_cli_asm.vm_create(self.params, options).exit_status

    def vm_update(self, params):
        """
        This helps to update VM info

        :param params: A dict containing VM params
        """
        if params is None:
            self.params = azure_cli_asm.vm_show(self.params["name"]).stdout
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
        ret = azure_cli_asm.vm_show(self.name)
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
        return azure_cli_asm.vm_restart(self.name, timeout=timeout).exit_status

    def start(self):
        """
        Starts this VM.
        """
        return azure_cli_asm.vm_start(self.name).exit_status

    def shutdown(self):
        """
        Shuts down this VM.
        """
        return azure_cli_asm.vm_shutdown(self.name).exit_status

    def delete(self, timeout=azure_vm.BaseVM.DELETE_TIMEOUT):
        """
        Delete this VM.

        :param timeout: Time to wait for deleting the VM.
        """
        return azure_cli_asm.vm_delete(self.name, timeout=timeout).exit_status

    def capture(self, vm_image_name, cmd_params=None,
                timeout=azure_vm.BaseVM.DEFAULT_TIMEOUT):
        """
        Capture this VM.
        """
        return azure_cli_asm.vm_capture(self.name, vm_image_name, cmd_params,
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


class Blob(object):

    """
    This class handles all basic storage blob operations for ASM.
    """
    DEFAULT_TIMEOUT = 240
    COPY_TIMEOUT = 240
    DELETE_TIMEOUT = 240

    def __init__(self, name, container, connection_string, params=None):
        """
        Initialize the object and set a few attributes.

        :param name: The name of the object
        :param params: A dict containing Blob params
        params sample:
        {
          "container": "vhds",
          "blob": "*.vhd",
          "metadata": {},
          "etag": "\"0x8D36282A848C391\"",
          "lastModified": "Tue, 12 Apr 2016 03:29:29 GMT",
          "contentType": "application/octet-stream",
          "contentMD5": "Op9zlFGBSO5gbl8jCcfyZQ==",
          "contentLength": "8589935104",
          "blobType": "PageBlob",
          "leaseStatus": "unlocked",
          "leaseState": "available",
          "sequenceNumber": "0",
          "copySource": "https://walaautoasmeastus.blob.core.windows.net/vhds/*.vhd",
          "copyStatus": "success",
          "copyCompletionTime": "Tue, 12 Apr 2016 03:29:29 GMT",
          "copyId": "b1b91d20-ad31-44e9-a6ab-f25a699d7e8b",
          "copyProgress": "8589935104/8589935104",
          "requestId": "c042618c-0001-00cc-0e1c-9642ca000000"
        }
        :return:
        """
        self.name = name
        self.container = container
        self.connection_string = connection_string
        if params:
            self.params = params
        else:
            self.update()
        logging.info("Azure Storage Blob '%s'", self.name)

    def copy(self, params, options='--quiet', timeout=COPY_TIMEOUT):
        """
        Start to copy the resource to the specified storage blob which
        completes asynchronously

        :param options: extra options
        :param params: A dict containing dest blob params
        :param timeout: Copy timeout
        :return:
        """
        params["source_container"] = self.params["container"]
        params["source_blob"] = self.params["blob"]
        params["source_blob"] = self.params["blob"]
        azure_cli_asm.blob_copy_start(params, options)
        start_time = time.time()
        end_time = start_time + timeout

        show_params = dict()
        show_params["connection_string"] = \
            params.get("dest_connection_string", None)
        show_params["account_name"] = params.get("dest_account_name", None)
        show_params["container"] = params.get("dest_container", None)
        show_params["blob"] = params.get("dest_blob", None)
        show_params["sas"] = params.get("dest_sas", None)
        rt = azure_cli_asm.blob_copy_show(show_params).stdout
        while time.time() < end_time:
            rt = azure_cli_asm.blob_copy_show(show_params).stdout
            if rt["copyStatus"] == "success":
                return True
            else:
                time.sleep(10)
        if rt["copyStatus"] == "pending":
            return False

    def show(self, params=None, options=''):
        """
        Show details of the specified storage blob

        :param params: Command properties
        :param options: extra options
        :return: params - A dict containing blob params
        """
        show_params = params.copy()
        show_params["container"] = self.container
        show_params["connection_string"] = self.connection_string
        return azure_cli_asm.blob_show(self.name, show_params, options).stdout

    def update(self):
        """
        Update details of the specified storage container

        :return:
        """
        self.params = self.show()


class Container(object):

    """
    This class handles all basic storage container operations for ASM.
    """
    DEFAULT_TIMEOUT = 240
    DELETE_TIMEOUT = 240

    def __init__(self, name, connection_string, params=None):
        """
        Initialize the object and set a few attributes.

        :param name: The name of the object
        :param params: A dict containing Blob params
        params sample:
            {
              "name": "vhds",
              "metadata": {},
              "etag": "\"0x8D33CD4D825553F\"",
              "lastModified": "Wed, 24 Feb 2016 04:42:04 GMT",
              "leaseStatus": "locked",
              "leaseState": "leased",
              "leaseDuration": "infinite",
              "requestId": "2ae50e0e-0001-003f-251c-96d279000000",
              "publicAccessLevel": "Off"
            }
        :return:
        """
        self.name = name
        self.connection_string = connection_string
        if params:
            self.params = params
        else:
            self.update()
        logging.info("Azure Storage Container '%s'", self.name)

    def show(self, params=None, options=''):
        """
        Show details of the specified storage blob

        :param params: Command properties
        :param options: extra options
        :return: params - A dict containing blob params
        """
        show_params = params.copy()
        show_params["connection_string"] = self.connection_string
        return azure_cli_asm.container_show(self.name, show_params,
                                            options=options).stdout

    def create(self, params=None, options=''):
        """
        Create a storage container

        :param params: Command properties
        :param options: extra options
        :return: params - A dict containing blob params
        """
        show_params = params.copy()
        show_params["connection_string"] = self.connection_string
        return azure_cli_asm.container_create(self.name, show_params,
                                              options=options).stdout

    def delete(self, params=None, options=''):
        """
        Create a storage container

        :param params: Command properties
        :param options: extra options
        :return: params - A dict containing blob params
        """
        show_params = params.copy()
        show_params["connection_string"] = self.connection_string
        return azure_cli_asm.container_delete(self.name, show_params,
                                              options=options).stdout

    def update(self):
        """
        Update details of the specified storage blob

        :return:
        """
        self.params = self.show()


class StorageAccount(object):

    """
    This class handles all basic storage account operations for ASM.
    """
    DEFAULT_TIMEOUT = 240
    DELETE_TIMEOUT = 240

    def __init__(self, name, params=None):
        """
        Initialize the object and set a few attributes.

        :param name: The name of the object
        :param params: A dict containing Storage Account params
         params sample:
            {
              "extendedProperties": {
                "ResourceGroup": "walaautoasmeastus",
                "ResourceLocation": "eastus"
              },
              "uri": "https://*/services/storageservices/walaautoasmeastus",
              "name": "walaautoasmeastus",
              "properties": {
                "endpoints": [
                  "https://walaautoasmeastus.blob.core.windows.net/",
                  "https://walaautoasmeastus.queue.core.windows.net/",
                  "https://walaautoasmeastus.table.core.windows.net/",
                  "https://walaautoasmeastus.file.core.windows.net/"
                ],
                "description": "walaautoasmeastus",
                "location": "East US",
                "label": "walaautoasmeastus",
                "status": "Created",
                "geoPrimaryRegion": "East US",
                "statusOfGeoPrimaryRegion": "Available",
                "geoSecondaryRegion": "West US",
                "statusOfGeoSecondaryRegion": "Available",
                "accountType": "Standard_RAGRS"
              },
              "resourceGroup": ""
            }
        """
        self.name = name
        self.mode = "ASM"
        self.params = params
        self.keys = None
        self.connectionstring = None
        logging.info("Azure Storage Account '%s'", self.name)

    def create(self, options=''):
        """
        This helps to create a Storage Account

        :param options: extra options
        :return: Zero if success to create VM
        """
        return azure_cli_asm.sto_acct_create(self.params, options).exit_status

    def update(self, params):
        """
        This helps to update Storage Account info

        :param params: A dict containing Storage Account params
        """
        if params is None:
            self.params = self.show().stdout
            self.keys = self.keys_list().stdout
            self.connectionstring = self.conn_show().stdout
        else:
            self.params = params

    def check_exist(self, options=''):
        """
        Help to check whether the account name is valid and is not in use

        :param options: extra options
        :return: True if exists
        """
        rt = azure_cli_asm.sto_acct_check(self.params["name"], options).stdout
        if rt.get("nameAvailable") == "false":
            return True
        else:
            return False

    def show(self, options=''):
        """
        Help to show a storage account

        :param options: extra options
        :return: params - A dict containing storage account params
        """
        return azure_cli_asm.sto_acct_show(self.params["name"], options).stdout

    def delete(self, options='', timeout=DELETE_TIMEOUT):
        """
        Help to delete a storage account

        :param options: extra options
        :param timeout: Delete timeout
        :return: Zero if success to delete VM
        """
        return azure_cli_asm.sto_acct_show(self.params["name"],
                                           options, timeout=timeout).exit_status

    def conn_show(self, options=''):
        """
        Help to show the connection string

        :param options: extra options
        """
        return azure_cli_asm.sto_acct_conn_show(self.params["name"],
                                                options).stdout

    def keys_list(self, options=''):
        """
        Help to list the keys for a storage account

        :param options: extra options
        """
        return azure_cli_asm.sto_acct_keys_list(self.params["name"],
                                                options).stdout
