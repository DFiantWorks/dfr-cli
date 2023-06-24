from dfr_scripts.common import GitOSSTool


class SpecificTool(GitOSSTool):
    def __init__(self, versionReq: str):
        super().__init__("vlsi", "iverilog", versionReq, "https://github.com/steveicarus/iverilog")

    def buildAndInstallShellCmd(self, flags: str) -> str:
        return f"""
                chmod +x autoconf.sh
                ./autoconf.sh
                ./configure --prefix={self.installPath()}
                make -j`nproc`
                sudo make install
                """

    def env_man_path(self) -> list[str]:
        return [f"{self.linkedPath()}/man"]
