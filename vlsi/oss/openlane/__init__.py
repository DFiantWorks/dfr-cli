from dfr_scripts.common import GitOSSTool


class SpecificTool(GitOSSTool):
    _useTags: bool = True

    def __init__(self, versionReq: str):
        super().__init__("vlsi", "openlane", versionReq, "https://github.com/The-OpenROAD-Project/OpenLane")

    def buildAndInstallShellCmd(self, flags: str) -> str:
        return f"""
                mkdir -p {self.installPath()}
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
        return {"OPENLANE_ROOT": self.linkedPath(), "OPENLANE_TAG": self.version}

    def cmdAliases(self) -> list[tuple[str, str]]:
        return [(f"{self.linkedPath()}/flow.tcl", "openlane")]

    def env_final_run(self) -> str:
        return f"cp /{self.linkedPath()}/dependencies/tool_metadata.yml /"
