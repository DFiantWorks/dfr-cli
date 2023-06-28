from dfr_scripts.common import GitPythonOSSTool


class SpecificTool(GitPythonOSSTool):
    def __init__(self, versionReq: str):
        super().__init__(
            "vlsi", "pythondata_misc_tapcfg", versionReq, "https://github.com/litex-hub/pythondata-misc-tapcfg"
        )
