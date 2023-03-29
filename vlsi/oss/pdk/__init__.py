from dfr_scripts.common import ZeroInstallTool


class SpecificTool(ZeroInstallTool):
    def actualVersion(self, toolMnt: str, versionReq: str) -> str:
        if versionReq in {"sky130A", "sky130B", "gf180mcuA", "gf180mcuB", "gf180mcuC"}:
            return versionReq
        else:
            return ""

    def __init__(self, versionReq: str):
        super().__init__("vlsi", "oss", "pdk", versionReq)

    def env_extra(self) -> dict[str, str]:
        return {"PDK": self.version}
