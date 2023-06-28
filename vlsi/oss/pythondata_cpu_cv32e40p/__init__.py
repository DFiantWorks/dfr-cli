from dfr_scripts.common import GitPythonOSSTool


class SpecificTool(GitPythonOSSTool):
    def __init__(self, versionReq: str):
        super().__init__(
            "vlsi", "pythondata_cpu_cv32e40p", versionReq, "https://github.com/litex-hub/pythondata-cpu-cv32e40p"
        )

    def recursiveClone(self) -> bool:
        return True
