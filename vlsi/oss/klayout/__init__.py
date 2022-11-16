from dfr_scripts.common import GitOSSTool

# TODO: figure out why the openlane docker installation of klayout is so different
class SpecificTool(GitOSSTool):
    def __init__(self, versionReq: str):
        super().__init__("vlsi", "klayout", versionReq, "https://github.com/KLayout/klayout")

    def buildAndInstallShellCmd(self, flags: str) -> str:
        return f"""
                mkdir -p {self.installPath()}
                ./build.sh -j`nproc` -prefix {self.installPath()} -without-qtbinding
                """

    def execFolder(self) -> str:
        return ""
