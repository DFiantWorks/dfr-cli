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
                sudo make -j`nproc` install
                sudo cp -r ../bin {self.installPath()}/
                sudo cp -r ../lib {self.installPath()}/
                sudo cp -r ../frameworks {self.installPath()}/
                sudo mkdir -p {self.installPath()}/src
                sudo cp -r ../src/libs {self.installPath()}/src/
                """
