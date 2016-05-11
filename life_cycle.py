import time

from avocado import Test
from avocado import main

from azuretest import azure_cli_common
from azuretest import azure_asm_vm
from azuretest import azure_image


def collect_vm_params(params):
    return


class LifeCycleTest(Test):

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
        self.vm_params["VMSize"] = self.params.get('vm_size', '*/life_cycle/*')
        self.vm_params["VMName"] = self.params.get('vm_name', '*/life_cycle/*')
        self.vm_params["VMName"] += "-" + self.vm_params["VMSize"]
        self.vm_params["DNSName"] = self.vm_params["VMName"]
        self.vm_params["Image"] = self.params.get('name', '*/Image/*')
        self.vm_params["Location"] = self.params.get('location', '*/Image/*')
        self.vm_test01 = azure_asm_vm.VMASM(self.vm_params["VMName"],
                                            self.vm_params["VMSize"],
                                            self.vm_params)
        self.log.debug("Create the vm %s", self.vm_params["VMName"])
        self.vm_test01.vm_create()
        self.vm_test01.start()

    def test_restart_vm(self):
        """
        restart

        :return:
        """
        self.log.debug("Restart the vm %s", self.vm_params["VMName"])
        self.assertEqual(self.vm_test01.restart(), 0,
                         "Fails to restart the vm")

    def test_shutdown_vm(self):
        """
        shutdown

        :return:
        """
        self.log.debug("Shutdown the vm %s", self.vm_params["VMName"])
        self.assertEqual(self.vm_test01.shutdown(), 0,
                         "Fails to shutdown the vm")

    def test_start_vm(self):
        """
        start

        :return:
        """
        self.log.debug("Shutdown the vm %s first", self.vm_params["VMName"])
        self.vm_test01.shutdown()
        self.log.debug("Start the vm %s", self.vm_params["VMName"])
        self.assertEqual(self.vm_test01.start(), 0,
                         "Fails to start the vm")

    def test_capture_vm(self):
        """
        capture

        :return:
        """
        self.log.debug("Capture the vm %s", self.vm_params["VMName"])
        postfix = time.strftime("-%m%d%H%M%S")
        capture_vm_name = self.vm_params["VMName"] + postfix
        capture_image = azure_image.VMImage(name=capture_vm_name)

        cmd_params = dict()
        cmd_params["os_state"] = "Specialized"
        self.assertEqual(self.vm_test01.capture(capture_image.name, cmd_params),
                         0, "Fails to capture the vm!")
        self.assertEqual(capture_image.verify_exist(), 0,
                         "Fails to get the captured vm image!")
        capture_image.vm_image_update()
        self.log.debug("Success to capture the vm as image %s",
                       capture_image.name)

if __name__ == "__main__":
    main()
