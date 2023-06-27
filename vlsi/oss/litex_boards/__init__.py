from dfr_scripts.common import GitPythonOSSTool


class SpecificTool(GitPythonOSSTool):
    def __init__(self, versionReq: str):
        super().__init__("vlsi", "litex_boards", versionReq, "https://github.com/litex-hub/litex-boards")
