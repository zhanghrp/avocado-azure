import time

from avocado import Test
from avocado import main

from azuretest import azure_cli_common
from azuretest import azure_asm_vm
from azuretest import azure_arm_vm
from azuretest import azure_image


def collect_vm_params(params):
    return


class StorageTest(Test):

    def setUp(self):
        # Login Azure and change the mode
        self.azure_username = self.params.get('username', '*/AzureSub/*')
        self.azure_password = self.params.get('password', '*/AzureSub/*')
        self.azure_mode = self.params.get('azure_mode', '*/storage/*')
        azure_cli_common.login_azure(username=self.azure_username,
                                     password=self.azure_password)

        # Prepare the vm parameters and create a vm
        self.vm_params = dict()
        self.vm_params["username"] = self.params.get('username', '*/VMUser/*')
        self.vm_params["password"] = self.params.get('password', '*/VMUser/*')
        self.vm_params["VMSize"] = self.params.get('vm_size', '*/wala_conf/*')
        self.vm_params["VMName"] = self.params.get('vm_name', '*/wala_conf/*')
        self.vm_params["DNSName"] = self.vm_params["VMName"]
        self.vm_params["Image"] = self.params.get('name', '*/Image/*')
        self.vm_params["Location"] = self.params.get('location', '*/Image/*')
        self.vm_params["VMName"] = self.params.get('vm_name', '*/wala_conf/*')

        if self.azure_mode == "asm":
            azure_cli_common.set_config_mode("asm")
            self.vm_test01 = azure_asm_vm.VMASM(self.vm_params["VMName"],
                                                self.vm_params["VMSize"],
                                                self.vm_params)
        elif self.azure_mode == "arm":
            azure_cli_common.set_config_mode("asm")
            self.vm_test01 = azure_arm_vm.VMARM(self.vm_params["VMName"],
                                                self.vm_params["VMSize"],
                                                self.vm_params)

        self.log.debug("Create the vm %s", self.vm_params["VMName"])
        self.vm_test01.vm_create()
        self.vm_test01.start()

    def test_disk_attach_new(self):
        """
        Attach a new disk to the VM

        :return:
        """
        self.log.debug("Attach a new disk to the vm %s", self.vm_params["VMName"])
        self.vm_test01.disk_attach_new()

if __name__ == "__main__":
    main()
