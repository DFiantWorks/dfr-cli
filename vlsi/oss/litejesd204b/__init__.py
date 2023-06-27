from dfr_scripts.common import GitPythonOSSTool


class SpecificTool(GitPythonOSSTool):
    def __init__(self, versionReq: str):
        super().__init__("vlsi", "litejesd204b", versionReq, "https://github.com/enjoy-digital/litejesd204b")
