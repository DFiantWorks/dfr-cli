from dfr_scripts.common import GitPythonOSSTool


class SpecificTool(GitPythonOSSTool):
    def __init__(self, versionReq: str):
        super().__init__("vlsi", "liteiclink", versionReq, "https://github.com/enjoy-digital/liteiclink")
