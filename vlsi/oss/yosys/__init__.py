from dfr_scripts.common import GitOSSTool

class SpecificTool(GitOSSTool):
  def __init__(self, version: str):
    super().__init__("vlsi", "yosys", version, "https://github.com/YosysHQ/yosys")
  def buildAndInstallShellCmd(self, flags: str) -> str:
    return f"""
      make PREFIX={self.installPath()} config-gcc
      make PREFIX={self.installPath()} -j`nproc`
      make PREFIX={self.installPath()} install
    """

