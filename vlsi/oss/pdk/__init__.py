from dfr_scripts.common import ZeroInstallTool, VersionLoc


class SpecificTool(ZeroInstallTool):
    def latestInstalledVersion(self, versionReq: str) -> VersionLoc:
        toolMnt = "mytools"
        if versionReq in {"sky130A", "sky130B", "gf180mcuA", "gf180mcuB", "gf180mcuC"}:
            return VersionLoc(toolMnt, versionReq)
        else:
            return VersionLoc(toolMnt, "")

    def __init__(self, versionReq: str):
        super().__init__("vlsi", "oss", "pdk", versionReq)

    def env_extra(self) -> dict[str, str]:
        return {"PDK": self.versionLoc.version}
