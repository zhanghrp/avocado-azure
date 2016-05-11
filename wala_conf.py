import time

from avocado import Test
from avocado import main

from azuretest import azure_cli_common
from azuretest import azure_asm_vm
from azuretest import azure_image


def collect_vm_params(params):
    return


class WALAConfTest(Test):

    def setUp(self):
        # Login Azure and change the mode
        self.azure_username = self.params.get('username', '*/AzureSub/*')
        self.azure_password = self.params.get('password', '*/AzureSub/*')
        azure_cli_common.login_azure(username=self.azure_username,
                                     password=self.azure_password)
        azure_cli_common.set_config_mode("asm")

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
        self.vm_test01 = azure_asm_vm.VMASM(self.vm_params["VMName"],
                                            self.vm_params["VMSize"],
                                            self.vm_params)
        self.log.debug("Create the vm %s", self.vm_params["VMName"])
        self.vm_test01.vm_create()
        self.vm_test01.start()

    def test_delete_root_passwd(self):
        """
        Check
        Provisioning.DeleteRootPassword = n And y

        :return:
        """
        self.log.debug("Restart the vm %s", self.vm_params["VMName"])
        self.assertEqual(self.vm_test01.restart(), 0,
                         "Fails to restart the vm")

if __name__ == "__main__":
    main()
