import subprocess
import shlex
import os
import shutil
import textwrap
from dfr_scripts.common import AMDTool, Download


class SpecificTool(AMDTool):
    def __init__(self, versionReq: str):
        super().__init__("vivado", versionReq)

    # the AMD installation forced the folder name to be `Vivado`
    def _toolPathNoVersion(self, toolMnt: str) -> str:
        return f"/mnt/{toolMnt}/{self.domain}/{self.vendor}/Vivado"

    def versionDownloadMap(self) -> dict[str, Download]:
        def dl(fileName: str, date: str) -> Download:
            return Download(
                url=f"https://www.xilinx.com/member/forms/download/xef.html?filename={fileName}",
                fileName=fileName,
                date=date,
            )

        return {
            "2023.1": dl("Xilinx_Unified_2023.1_0507_1903_Lin64.bin", "20230517"),
            "2022.2": dl("Xilinx_Unified_2022.2_1014_8888_Lin64.bin", "20221019"),
            "2022.1": dl("Xilinx_Unified_2022.1_0420_0327_Lin64.bin", "20220426"),
            "2021.2": dl("Xilinx_Unified_2021.2_1021_0703_Lin64.bin", "20211027"),
            "2021.1": dl("Xilinx_Unified_2021.1_0610_2318_Lin64.bin", "20210622"),
            "2020.3": dl("Xilinx_Unified_2020.3_0407_2214_Lin64.bin", "20210417"),
            "2020.2": dl("Xilinx_Unified_2020.2_1118_1232_Lin64.bin", "20201124"),
            "2020.1": dl("Xilinx_Unified_2020.1_0602_1208_Lin64.bin", "20200812"),
            "2019.2": dl("Xilinx_Unified_2019.2_1106_2127_Lin64.bin", "20191211"),
        }

    installerFolder = "/tmp/amd"
    installerExec = f"{installerFolder}/xsetup"
    installerConfig = f"{installerFolder}/install_config.txt"
    configGenDefaultFile = os.path.expanduser("~/.Xilinx/install_config.txt")

    def extract(self, downloadedFilePath: str):
        if os.path.exists(self.installerFolder):
            shutil.rmtree(self.installerFolder)
        os.chmod(downloadedFilePath, 0o777)
        subprocess.run(shlex.split(f"{downloadedFilePath} --keep --noexec --target {self.installerFolder}"))

    def postDownloadInstall(self, date: str, flags: str):
        if flags == "__GEN_CFG__":
            print("Generating config...")
            subprocess.run(shlex.split(f"{self.installerExec} -b ConfigGen"))
            dest = os.path.expanduser(f"~/Downloads/install_config_{self.versionLoc.version}.txt")
            shutil.copy(self.configGenDefaultFile, dest)
            print(f"Created config file at: {dest}")
        else:
            template = f"{os.path.dirname(os.path.realpath(__file__))}/install_config_{self.versionLoc.version}.txt"
            with open(template, "r") as file:
                lines = file.readlines()
            with open(self.installerConfig, "w") as file:
                for line in lines:
                    if line.startswith("Destination="):
                        line = f"Destination=/mnt/{self.versionLoc.toolMnt}/{self.domain}/{self.vendor}\n"
                    file.write(line)

            subprocess.run(
                textwrap.dedent(
                    f"""
                    set -e
                    echo Running token generation...
                    sudo {self.installerExec} -b AuthTokenGen
                    echo Running setup...
                    sudo {self.installerExec} -b Install -a XilinxEULA,3rdPartyEULA -c {self.installerConfig}
                    sudo touch -a -m -t {date}0000 {self.installDirReadyFilePath()}
                    """
                ),
                shell=True,
            )

        shutil.rmtree(self.installerFolder)

    # removing default addition of vivado binary to path because this is handled by `settings64.sh`
    def env_path(self) -> list[str]:
        return []

    # handles most of the required vivado environment
    def env_sources(self) -> list[str]:
        return [f"{self.installPath()}/settings64.sh"]

    # LD_PRELOAD=... is a workaround for Vivado segfault with docker in Ubuntu 20+
    # see https://support.xilinx.com/s/question/0D54U00005Sgst2SAB/failed-batch-mode-execution-in-linux-docker-running-under-windows-host?language=en_US
    def env_extra(self) -> dict[str, str]:
        return {"LD_PRELOAD": "/lib/x86_64-linux-gnu/libudev.so.1"}
