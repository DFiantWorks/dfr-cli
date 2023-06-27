import sys
from dfr_scripts.common import GitOSSTool, downloadAvailable


class SpecificTool(GitOSSTool):
    def __init__(self, versionReq: str):
        super().__init__("vlsi", "openpdks", versionReq, "https://github.com/RTimothyEdwards/open_pdks")

    def pdkCmd(self, pdk: str) -> str:
        url = f"https://github.com/efabless/volare/releases/download/{pdk}-{self.versionLoc.version}/default.tar.xz"
        if downloadAvailable(url):
            return f"""
                    cd {self.installPath()}
                    curl -L {url} | sudo tar -xJC .
                    """
        else:
            return ""

    def buildAndInstallShellCmd(self, flags: str) -> str:
        sky130Cmd = self.pdkCmd("sky130")
        gf180mcu = self.pdkCmd("gf180mcu")
        if sky130Cmd == "" and gf180mcu == "":
            print(f"Could not find PDK download link for {self.versionLoc.version}")
            sys.exit(1)
        return f"""
                {sky130Cmd}
                {gf180mcu}
                """

    def env_path(self) -> list[str]:
        return []

    def env_extra(self) -> dict[str, str]:
        return {"PDK_ROOT": self.linkedPath()}
