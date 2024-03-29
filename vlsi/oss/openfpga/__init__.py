from dfr_scripts.common import GitOSSTool


class SpecificTool(GitOSSTool):
    def __init__(self, versionReq: str):
        super().__init__("vlsi", "openfpga", versionReq, "https://github.com/LNIS-Projects/OpenFPGA")

    def dependencies(self) -> dict[str, str]:
        ret: dict[str, str] = {
            "vlsi.oss.yosys": self.getGitSubmoduleCommit("yosys"),
            "vlsi.oss.yosys_f4pga_plugins": self.getGitSubmoduleCommit("yosys-plugins"),
        }
        vtr = self.getGitSubmoduleCommit("vtr-verilog-to-routing")
        if vtr:
            ret["vlsi.oss.vtr"] = vtr
        return ret

    def recursiveClone(self) -> bool:
        return True

    def acceptCloneError(self) -> bool:
        return True

    def buildAndInstallShellCmd(self, flags: str) -> str:
        # CMAKE_FLAGS="-DOPENFPGA_WITH_YOSYS=OFF -DOPENFPGA_WITH_YOSYS_PLUGIN=OFF"
        return f"""
                make all -j`nproc` 
                sudo cp -avr . {self.installPath()}
                """

    def env_extra(self) -> dict[str, str]:
        return {"OPENFPGA_PATH": self.linkedPath()}

    def env_sources(self) -> list[str]:
        return [f"{self.linkedPath()}/openfpga.sh"]
