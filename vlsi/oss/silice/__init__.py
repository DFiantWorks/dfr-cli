from dfr_scripts.common import GitOSSTool


class SpecificTool(GitOSSTool):
    def __init__(self, versionReq: str):
        super().__init__("vlsi", "silice", versionReq, "https://github.com/sylefeb/Silice")

    def recursiveClone(self) -> bool:
        return True

    def buildAndInstallShellCmd(self, flags: str) -> str:
        return f"""
                mkdir -p build
                cd build
                cmake -DCMAKE_BUILD_TYPE=Release -G "Unix Makefiles" ..
                make -j`nproc` install
                cp -r ../bin {self.installPath()}/
                cp -r ../lib {self.installPath()}/
                cp -r ../frameworks {self.installPath()}/
                mkdir -p {self.installPath()}/src
                cp -r ../src/libs {self.installPath()}/src/
                """
