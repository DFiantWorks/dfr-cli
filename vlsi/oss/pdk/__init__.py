from dfr_scripts.common import ZeroInstallTool

class SpecificTool(ZeroInstallTool):
  def __init__(self, versionReq: str):
    super().__init__("vlsi", "oss", "pdk", versionReq)
  def env_extra(self) -> dict[str, str]:
    return {"PDK" : self.version}


