import subprocess
import shlex
import os
import shutil
from dfr_scripts.vlsi.amd import AMDTool
from typing import Dict


class SpecificTool(AMDTool):
    def __init__(self, versionReq: str):
        super().__init__("vivado", versionReq)

    def versionToFileNameMap(self) -> Dict[str, str]:
        return {
            "2023.1": "Xilinx_Unified_2023.1_0507_1903_Lin64.bin",
            "2022.2": "Xilinx_Unified_2022.2_1014_8888_Lin64.bin",
            "2022.1": "Xilinx_Unified_2022.1_0420_0327_Lin64.bin",
            "2021.2": "Xilinx_Unified_2021.2_1021_0703_Lin64.bin",
            "2021.1": "Xilinx_Unified_2021.1_0610_2318_Lin64.bin",
            "2020.3": "Xilinx_Unified_2020.3_0407_2214_Lin64.bin",
            "2020.2": "Xilinx_Unified_2020.2_1118_1232_Lin64.bin",
            "2020.1": "Xilinx_Unified_2020.1_0602_1208_Lin64.bin",
            "2019.2": "Xilinx_Unified_2019.2_1106_2127_Lin64.bin",
        }

    installerFolder = "/tmp/amd"
    installerExec = f"{installerFolder}/xsetup"
    configGenDefaultFile = os.path.expanduser("~/.Xilinx/install_config.txt")

    def extract(self):
        if os.path.exists(self.installerFolder):
            shutil.rmtree(self.installerFolder)
        downloadedFilePath = self.downloadedFilePath()
        os.chmod(downloadedFilePath, 0o777)
        subprocess.run(shlex.split(f"{downloadedFilePath} --keep --noexec --target {self.installerFolder}"))

    def postDownloadInstall(self, flags: str):
        if flags == "__GEN_CFG__":
            print("Generating config...")
            subprocess.run(shlex.split(f"{self.installerExec} -b ConfigGen"))
            dest = os.path.expanduser(f"~/Downloads/install_config_{self.versionLoc.version}.txt")
            shutil.copy(self.configGenDefaultFile, dest)
            print(f"Created config file at: {dest}")
        else:
            print("Running token generation...")
            subprocess.run(shlex.split(f"{self.installerExec} -b AuthTokenGen"))
            print("Running setup...")
        shutil.rmtree(self.installerFolder)
