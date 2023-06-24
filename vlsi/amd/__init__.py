from dfr_scripts.common import InteractivelyDownloadedTool
from typing import Dict
from abc import abstractmethod


class AMDTool(InteractivelyDownloadedTool):
    def __init__(self, name: str, versionReq: str):
        super().__init__("vlsi", "amd", name, versionReq)

    @abstractmethod
    def versionToFileNameMap(self) -> Dict[str, str]:
        pass

    # TODO: consider replacing with webcrawling techniques instead of a fixed lookup
    def downloadFileName(self) -> str:
        try:
            return self.versionToFileNameMap()[self.versionLoc.version]
        except:
            return self.unsupportedVersionErr()

    def downloadURL(self) -> str:
        return f"https://www.xilinx.com/member/forms/download/xef.html?filename={self.downloadFileName()}"

    def downloadInstructions(self) -> str:
        return "Login with your Xilinx account and then click on the Download button at the bottom of the page."
