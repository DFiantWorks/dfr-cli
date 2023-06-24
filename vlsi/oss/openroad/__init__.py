from dfr_scripts.common import GitOSSTool


class SpecificTool(GitOSSTool):
    def __init__(self, versionReq: str):
        super().__init__("vlsi", "openroad", versionReq, "https://github.com/The-OpenROAD-Project/OpenROAD")

    def recursiveClone(self) -> bool:
        return True

    def buildAndInstallShellCmd(self, flags: str) -> str:
        return f"""
                mkdir -p build
                cd build
                cmake .. -DCMAKE_INSTALL_PREFIX={self.installPath()}
                make -j`nproc`  
                sudo make install
                """

    def env_path(self) -> list[str]:
        return [
            f"{self.linkedPath()}/{self.execFolder()}",
            f"{self.linkedPath()}/{self.execFolder()}/Linux-x86_64",
            f"{self.linkedPath()}/pdn/scripts",
        ]

    def env_man_path(self) -> list[str]:
        return [f"{self.linkedPath()}/share/man"]

    def env_ld_library_path(self) -> list[str]:
        return [
            f"{self.linkedPath()}/lib",
            f"{self.linkedPath()}/lib/Linux-x86_64",
        ]

    def env_extra(self) -> dict[str, str]:
        return {"OPENROAD": self.linkedPath(), "OPENROAD_BIN": "openroad"}
