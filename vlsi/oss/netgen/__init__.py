from dfr_scripts.common import GitOSSTool

class SpecificTool(GitOSSTool):
  def __init__(self, version: str):
    super().__init__("vlsi", "netgen", version, "https://github.com/rtimothyedwards/netgen")
  def buildAndInstallShellCmd(self, flags: str) -> str:
    return f"""
      ./configure --prefix={self.installPath()}
      make -j`nproc`
      make install
    """

