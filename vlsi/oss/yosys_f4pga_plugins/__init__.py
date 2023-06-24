from dfr_scripts.common import GitOSSTool


# TODO: these plugins require yosys environment setup
class SpecificTool(GitOSSTool):
    def __init__(self, versionReq: str):
        super().__init__(
            "vlsi", "yosys_f4pga_plugins", versionReq, "https://github.com/chipsalliance/yosys-f4pga-plugins"
        )

    def buildAndInstallShellCmd(self, flags: str) -> str:
        return f"""
                make PREFIX={self.installPath()} -j`nproc`
                sudo make PREFIX={self.installPath()} install
                """
