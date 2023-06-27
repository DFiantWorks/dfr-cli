from dfr_scripts.common import GitPythonOSSTool


class SpecificTool(GitPythonOSSTool):
    def __init__(self, versionReq: str):
        super().__init__(
            "vlsi",
            "pythondata_software_compiler_rt",
            versionReq,
            "https://github.com/litex-hub/pythondata-software-compiler_rt",
        )

    def recursiveClone(self) -> bool:
        return True
