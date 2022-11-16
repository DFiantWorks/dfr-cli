from dfr_scripts.common import GitOSSTool

# TODO: Add integration with SystemC https://verilator.org/guide/latest/install.html#install-systemc
class SpecificTool(GitOSSTool):
    def __init__(self, versionReq: str):
        super().__init__("vlsi", "verilator", versionReq, "https://github.com/verilator/verilator")

    def buildAndInstallShellCmd(self, flags: str) -> str:
        return f"""
                unset VERILATOR_ROOT
                autoconf         
                ./configure --prefix {self.installPath()}
                make -j`nproc`  
                make install
                """

    def env_man_path(self) -> list[str]:
        return [f"{self.linkedPath()}/man"]

    def env_pkg_config_path(self) -> list[str]:
        return [f"{self.linkedPath()}/share/pkgconfig"]
