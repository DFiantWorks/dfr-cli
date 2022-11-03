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

def addEnvPaths(envName: str, paths: list[str]) -> None:
  if len(os.environ.get(envName, '')) == 0:
    os.environ[envName] = ':'.join(paths)
  else:
    os.environ[envName] = f"{os.environ[envName]}:{':'.join(paths)}"

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
  def installPath(self) -> str:
    return f"{paths.INSTALL}/{self.domain}/{self.vendor}/{self.name}/${self.version}"
  def linkedPath(self) -> str:
    return f"/opt/{self.name}"
  def execFolder(self) -> str:
    return "bin"
  #command aliases to be created [<origin path> : <alias name>]
  #by default, empty list
  def cmdAliases(self) -> list[tuple[str, str]]:
    return []
  #symbolic links to be created [<origin path> : <link path>]
  #by default, adding a link between install path and the defined linked path
  def symlinks(self) -> list[tuple[str, str]]:
    return [(self.installPath(), self.linkedPath())]
  #added paths to the path environment variable
  #by default, adding the execution path as determined by the linked path and execution folder
  def env_path(self) -> list[str]:
    return [f"{self.linkedPath()}/{self.execFolder()}"]
  #added python paths to the python path environment variable
  #by default, empty list
  def env_python_path(self) -> list[str]:
    return []
  #added ld_library paths to the ld_library path environment variable
  #by default, empty list
  def env_ld_library_path(self) -> list[str]:
    return []
  #added man paths to the man path environment variable
  #by default, empty list
  def env_man_path(self) -> list[str]:
    return []
  #added other environment variables {<var_name> : <value>, ...}
  #by default, empty dict
  def env_extra(self) -> dict[str, str]:
    return {}
  #the initial environment setup that includes environment variables,
  #symlinks, and command aliases
  def setup_env(self):
    addEnvPaths("PATH", self.env_path())
    addEnvPaths("PYTHONPATH", self.env_python_path())
    addEnvPaths("LD_LIBRARY_PATH", self.env_ld_library_path())
    addEnvPaths("MANPATH", self.env_man_path())
    for env in self.env_extra().items:
      os.environ[env[0]] = env[1]
    for symlink in self.symlinks():
      os.symlink(symlink[0], symlink[1])
    for cmdAlias in self.cmdAliases():
      with open(f'/usr/bin/{cmdAlias[1]}', 'w') as f:
        f.write('#!/bin/bash\n')
        f.write(f'{cmdAlias[0]} "$@"')
      os.chmod(f'/usr/bin/{cmdAlias[1]}', 0o777)          


class Tools:
  all: list[Tool] = []
  def __init__(self, tool_versions_flat: dict[str, str]): 
    sys.path.append(paths.TOOLS) #to allow import of dfr_scripts
    for toolModulePath, version in tool_versions_flat.items():
      module = importlib.import_module(f"dfr_scripts.{toolModulePath}")
      self.all.append(module.SpecificTool(version))
  def setup_env(self):
    for t in all:
      t.setup_env()

      
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
