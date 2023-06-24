from dfr_scripts.common import GitOSSTool


# TODO: Rely on dependencies instead of recursive clone. See Makelists.txt for flags.
class SpecificTool(GitOSSTool):
    def __init__(self, versionReq: str):
        super().__init__("vlsi", "surelog", versionReq, "https://github.com/chipsalliance/Surelog")

    # def dependencies(self) -> dict[str, str]:
    #     return {
    #         "vlsi.oss.uhdm": self.getGitSubmoduleCommit("thirdparty/uhdm"),
    #         "gen.oss.antlr4": self.getGitSubmoduleCommit("thirdparty/antlr4"),
    #         "gen.oss.flatbuffers": self.getGitSubmoduleCommit("thirdparty/flatbuffers"),
    #         "gen.oss.googletest": self.getGitSubmoduleCommit("thirdparty/googletest"),
    #     }

    def recursiveClone(self) -> bool:
        return True

    def buildAndInstallShellCmd(self, flags: str) -> str:
        return f"""
                make PREFIX={self.installPath()} -j`nproc`
                make PREFIX={self.installPath()} install
                """
