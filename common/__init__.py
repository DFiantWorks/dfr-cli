import subprocess
import shlex
import os
import time
import sys
import importlib
from typing import Dict
import stat

class Paths:
  TOOLS = "/mnt/tools"
  INSTALL = f"{TOOLS}/install"
  SCRIPTS = f"{TOOLS}/scripts"
  STAGING = f"{TOOLS}/staging"
  COMMON_SCRIPTS = f"{SCRIPTS}/common"

paths = Paths()

class Tool:
  domain: str
  vendor: str
  name: str
  version: str
  def __init__(self, domain: str, vendor: str, name: str, version: str):
    self.domain = domain
    self.vendor = vendor
    self.name = name
    self.version = version
  def stage(self):
    pass
  def build(self):
    pass
  def install(self, flags: str):
    pass
  def path(self) -> str:
    pass
  def env(self):
    pass

class Tools:
  all: list[Tool]
  def __init__(self, tool_versions_flat: dict[str, str]): 
    sys.path.append(paths.TOOLS) #to allow import of dfr_scripts
    for toolModulePath, version in tool_versions_flat.items():
      module = importlib.import_module(f"dfr_scripts.{toolModulePath}")
      self.all.append(module.tool(version))
      
class GitOSSTool(Tool):
  def __init__(self, domain: str, name: str, version: str, repo: str):
    super().__init__(domain, "oss", name, version)
    self.repo = repo
  def stage(self):
    pass

class InteractivelyDownloadedTool(Tool):
  def __init__(self, domain: str, vendor: str, name: str, version: str):
    super().__init__(domain, vendor, name, version)
  #all firefox downloads will be automatically placed here
  downloadsPath = "~/Downloads"
  def downloadFileName(self) -> str:
    pass
  def downloadedFilePath(self) -> str:
    f"{self.downloadsPath}{self.downloadFileName()}"
  def downloadURL(self) -> str:
    pass
  def downloadInstructions(self) -> str:
    pass
  def unsupportedVersionErr(self):
    print(f"Error: {self.name} version `{self.version}` is not supported.")
    sys.exit(1)

  def stage(self):
    print(f"(Remote) Firefox is now opening the {self.vendor} download page for you.")
    print(self.downloadInstructions())
    firefoxPid = subprocess.Popen(
      ['firefox', self.downloadURL()], 
      stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    downloadedFilePath = self.downloadedFilePath()
    print("Waiting for start of file download...")
    while not os.path.exists(downloadedFilePath):
      time.sleep(1)
    print("Start of download detected.")
    print("Waiting for end of download (do not close the firefox browser)...")
    while os.path.getsize(downloadedFilePath) == 0:
      time.sleep(1)
    print("Download completed!")
    firefoxPid.terminate()
    print("Extracting setup...")
    self.extract()
  def extract(self):
    pass


class XilinxTool(InteractivelyDownloadedTool):
  def __init__(self, name: str, version: str):
    super().__init__("vlsi", "Xilinx", name, version)
  def versionToFileNameMap(self) -> Dict[str, str]: 
    pass
  #TODO: consider replacing with webcrawling techniques instead of a fixed lookup
  def downloadFileName(self) -> str:
    try:
      self.versionToFileNameMap[self.version]
    except:
      self.unsupportedVersionErr()
  def downloadURL(self) -> str:
    f"https://www.xilinx.com/member/forms/download/xef.html?filename={self.downloadFileName()}"
  def downloadInstructions(self) -> str:
     "Login with your Xilinx account and then click on the Download button at the bottom of the page."


class Vivado(XilinxTool):
  def __init__(self, version: str):
    super().__init__("Vivado", version)
  def versionToFileNameMap(self) -> Dict[str, str]: {
    "2022.1": "Xilinx_Unified_2022.1_0420_0327_Lin64.bin",
    "2021.2": "Xilinx_Unified_2021.2_1021_0703_Lin64.bin",
    "2021.1": "Xilinx_Unified_2021.1_0610_2318_Lin64.bin",
    "2020.3": "Xilinx_Unified_2020.3_0407_2214_Lin64.bin",
    "2020.2": "Xilinx_Unified_2020.2_1118_1232_Lin64.bin",
    "2020.1": "Xilinx_Unified_2020.1_0602_1208_Lin64.bin",
  }
  def extract(self):
    downloadedFilePath = self.downloadedFilePath()
    os.chmod(downloadedFilePath, 0o777)
    subprocess.run(shlex.split(
      f"{downloadedFilePath} --keep --noexec --target {self.downloadsPath}"
    ))
