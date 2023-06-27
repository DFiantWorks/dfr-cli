from dfr_scripts.common import GitPythonOSSTool


class SpecificTool(GitPythonOSSTool):
    def __init__(self, versionReq: str):
        super().__init__(
            "vlsi",
            "pythondata_cpu_vexriscv_smp",
            versionReq,
            "https://github.com/litex-hub/pythondata-cpu-vexriscv-smp",
        )

    def recursiveClone(self) -> bool:
        return True
