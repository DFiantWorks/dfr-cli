from dfr_scripts.common import GitOSSTool


class SpecificTool(GitOSSTool):
    def __init__(self, versionReq: str):
        super().__init__("vlsi", "netgen", versionReq, "https://github.com/rtimothyedwards/netgen")

    def buildAndInstallShellCmd(self, flags: str) -> str:
        return f"""
                ./configure --prefix={self.installPath()}
                make -j`nproc`
                sudo make install
                """
