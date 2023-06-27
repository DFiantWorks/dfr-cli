from dfr_scripts.common import GitPythonOSSTool, isCommitVersion


class SpecificTool(GitPythonOSSTool):
    def __init__(self, versionReq: str):
        super().__init__("vlsi", "litex", versionReq, "https://github.com/enjoy-digital/litex")

    def dependencies(self) -> dict[str, str]:
        if isCommitVersion(self.versionReq):
            tag = "latest"
        else:
            tag = self.versionReq
        ret: dict[str, str] = {
            "vlsi.oss.migen": "latest",
            "vlsi.oss.pythondata_software_picolibc": "latest",
            "vlsi.oss.pythondata_software_compiler_rt": "latest",
            "vlsi.oss.litex_boards": tag,
            "vlsi.oss.liteeth": tag,
            "vlsi.oss.litedram": tag,
            "vlsi.oss.litepcie": tag,
            "vlsi.oss.litesata": tag,
            "vlsi.oss.litesdcard": tag,
            "vlsi.oss.liteiclink": tag,
            "vlsi.oss.litescope": tag,
            "vlsi.oss.litejesd204b": tag,
            "vlsi.oss.litespi": tag,
            "vlsi.oss.pythondata_cpu_vexriscv": "latest",
        }
        return ret
