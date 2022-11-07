import sys
from dfr_scripts.common import ShellInstallTool, downloadAvailable

class SpecificTool(ShellInstallTool):
  def __init__(self, version: str):
    super().__init__("vlsi", "oss", "openpdk", version)
  def pdkCmd(self, pdk: str) -> str:
    url = f"https://github.com/efabless/volare/releases/download/{pdk}-{self.version}/default.tar.xz"
    if downloadAvailable(url):
      return f"""
        wget {url}
        mkdir -p {self.installPath()}
        tar -xvf default.tar.xz -C {self.installPath()}
        rm default.tar.xz
      """    
    else:
      return ""
  def installShellCmd(self, flags: str) -> str:
    sky130Cmd = self.pdkCmd("sky130")
    gf180mcu = self.pdkCmd("gf180mcu")
    if sky130Cmd == "" and gf180mcu == "":
      print(f"Could not find PDK download link for {self.version}")
      sys.exit(1)
    return f"""
      set -e
      cd /tmp
      {sky130Cmd}
      {gf180mcu}
    """
  def env_path(self) -> list[str]:
    return []
  def env_extra(self) -> dict[str, str]:
    return {"PDK_ROOT" : self.linkedPath()}


