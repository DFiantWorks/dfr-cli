from dfr_scripts.common import GitOSSTool

class SpecificTool(GitOSSTool):
  def __init__(self, version: str):
    super().__init__("vlsi", "cvc", version, "https://github.com/d-m-bailey/cvc")
  def buildAndInstallShellCmd(self, flags: str) -> str:
    return f"""
      autoreconf -vif
      ./configure --disable-nls --prefix={self.installPath()}
      make -j`nproc`
      make install
    """

