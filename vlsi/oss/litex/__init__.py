from dfr_scripts.common import GitPythonOSSTool


class SpecificTool(GitPythonOSSTool):
    def __init__(self, versionReq: str):
        super().__init__("vlsi", "litex", versionReq, "https://github.com/enjoy-digital/litex")

    def dependencies(self) -> dict[str, str]:
        tag = self.versionReq
        ret: dict[str, str] = {
            "vlsi.oss.migen": "latest",
            # "vlsi.oss.pythondata_software_picolibc": "latest",
            # "vlsi.oss.pythondata-software-compiler_rt": "latest",
        }
        return ret
