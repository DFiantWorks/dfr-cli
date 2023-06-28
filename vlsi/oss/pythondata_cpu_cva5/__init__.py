from dfr_scripts.common import GitPythonOSSTool


class SpecificTool(GitPythonOSSTool):
    def __init__(self, versionReq: str):
        super().__init__("vlsi", "pythondata_cpu_cva5", versionReq, "https://github.com/litex-hub/pythondata-cpu-cva5")
