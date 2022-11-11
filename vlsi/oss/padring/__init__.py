from dfr_scripts.common import GitOSSTool


class SpecificTool(GitOSSTool):
    def __init__(self, versionReq: str):
        super().__init__("vlsi", "padring", versionReq, "https://github.com/donn/padring")

    def buildAndInstallShellCmd(self, flags: str) -> str:
        return f"""
      bash ./bootstrap.sh 
      cd build/ 
      ninja
      mkdir -p {self.installPath()}/bin 
      cp padring {self.installPath()}/bin/
    """
