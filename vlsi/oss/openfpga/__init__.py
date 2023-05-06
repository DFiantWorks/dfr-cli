from dfr_scripts.common import GitOSSTool


class SpecificTool(GitOSSTool):
    def __init__(self, versionReq: str):
        super().__init__("vlsi", "openfpga", versionReq, "https://github.com/LNIS-Projects/OpenFPGA.git")

    def buildAndInstallShellCmd(self, flags: str) -> str:
        return f"""
                apt update && apt install libpugixml-dev -y
                make all -j`nproc`
                cp -avr . {self.installPath()}
                """

    def env_extra(self) -> dict[str, str]:
        return {"OPENFPGA_PATH": self.linkedPath()}

    # TODO: need to be able to have start commands like: source openfpga.sh
