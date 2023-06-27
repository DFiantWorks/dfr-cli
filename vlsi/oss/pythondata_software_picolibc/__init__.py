from dfr_scripts.common import GitPythonOSSTool


class SpecificTool(GitPythonOSSTool):
    def __init__(self, versionReq: str):
        super().__init__(
            "vlsi",
            "pythondata_software_picolibc",
            versionReq,
            "https://github.com/litex-hub/pythondata-software-picolibc",
        )

    def recursiveClone(self) -> bool:
        return True
