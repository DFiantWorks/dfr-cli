from dfr_scripts.common import GitOSSTool

# TODO: figure out how to allow llvm and gcc versions
class SpecificTool(GitOSSTool):
    def __init__(self, versionReq: str):
        super().__init__("vlsi", "ghdl", versionReq, "https://github.com/ghdl/ghdl")

    def buildAndInstallShellCmd(self, flags: str) -> str:
        return f"""
      ./configure --prefix={self.installPath()}
      make -j`nproc`
      make install
    """
