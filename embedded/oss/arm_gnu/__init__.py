import sys
from dfr_scripts.common import GitOSSTool, downloadAvailable

# WIP!!!
# new versions: https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads
# old versions: https://developer.arm.com/downloads/-/gnu-rm
#  curl -L https://armkeil.blob.core.windows.net/developer/Files/downloads/gnu/12.2.mpacbti-bet1/binrel/arm-gnu-toolchain-12.2.mpacbti-bet1-darwin-x86_64-arm-none-eabi.tar.xz | tar -xJC . --strip-components=1
class SpecificTool(GitOSSTool):
    def __init__(self, versionReq: str):
        super().__init__("embedded", "arm_gnu", versionReq, "https://github.com/RTimothyEdwards/open_pdks")

    def pdkCmd(self, pdk: str) -> str:
        url = f"https://github.com/efabless/volare/releases/download/{pdk}-{self.version}/default.tar.xz"
        if downloadAvailable(url):
            return f"""
                    wget {url}
                    mkdir -p {self.installPath()}
                    tar -xvf default.tar.xz -C {self.installPath()}
                    rm default.tar.xz
                    """
        else:
            return ""

    def buildAndInstallShellCmd(self, flags: str) -> str:
        sky130Cmd = self.pdkCmd("sky130")
        gf180mcu = self.pdkCmd("gf180mcu")
        if sky130Cmd == "" and gf180mcu == "":
            print(f"Could not find PDK download link for {self.version}")
            sys.exit(1)
        return f"""
                mkdir build
                cd build
                {sky130Cmd}
                {gf180mcu}
                """

    def env_path(self) -> list[str]:
        return []

    def env_extra(self) -> dict[str, str]:
        return {"PDK_ROOT": self.linkedPath()}
