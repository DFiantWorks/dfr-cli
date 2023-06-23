from dfr_scripts.common import GitOSSTool
import yaml

dependencies: set[str] = {
    "vlsi.oss.cvc",
    "vlsi.oss.klayout",
    "vlsi.oss.magic",
    "vlsi.oss.netgen",
    "vlsi.oss.openpdks",
    "vlsi.oss.openroad",
    "vlsi.oss.padring",
    "vlsi.oss.qflow",
    "vlsi.oss.yosys",
}


class SpecificTool(GitOSSTool):
    _useTags: bool = True

    def __init__(self, versionReq: str):
        super().__init__("vlsi", "openlane", versionReq, "https://github.com/The-OpenROAD-Project/OpenLane")

    def dependencies(self) -> dict[str, str]:
        ret: dict[str, str] = {}
        with open(f"{self.installPath()}/dependencies/tool_metadata.yml") as file:
            tool_metadata = yaml.safe_load(file)
            for tool in tool_metadata:
                name = tool["name"]
                commit = tool["commit"]
                if name in {"cvc", "cvc_rv"}:
                    ret["vlsi.oss.cvc"] = commit
                if name == "klayout":
                    ret["vlsi.oss.klayout"] = commit
                if name == "magic":
                    ret["vlsi.oss.magic"] = commit
                if name == "netgen":
                    ret["vlsi.oss.netgen"] = commit
                if name == "open_pdks":
                    ret["vlsi.oss.openpdks"] = commit
                if name == "openroad_app":
                    ret["vlsi.oss.openroad"] = commit
                if name == "padring":
                    ret["vlsi.oss.padring"] = commit
                if name == "vlogtoverilog":
                    ret["vlsi.oss.qflow"] = commit
                if name == "yosys":
                    ret["vlsi.oss.yosys"] = commit
        return ret

    def siblings(self) -> set[str]:
        return {"vlsi.oss.pdk"}

    def buildAndInstallShellCmd(self, flags: str) -> str:
        return f"""
                rm -rf *.git
                rm -rf *.github
                rm -rf designs
                rm -rf docker
                cp -r * {self.installPath()}/
                """

    def env_path(self) -> list[str]:
        return [
            f"{self.linkedPath()}",
            f"{self.linkedPath()}/scripts",
        ]

    def env_extra(self) -> dict[str, str]:
        return {"OPENLANE_ROOT": self.linkedPath(), "OPENLANE_TAG": self.versionLoc.version}

    def cmdAliases(self) -> list[tuple[str, str]]:
        return [(f"{self.linkedPath()}/flow.tcl", "openlane")]

    def env_final_run(self) -> str:
        return f"cp {self.linkedPath()}/dependencies/tool_metadata.yml /"
