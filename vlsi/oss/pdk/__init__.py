from dfr_scripts.common import ZeroInstallTool

class SpecificTool(ZeroInstallTool):
  def __init__(self, version: str):
    super().__init__("vlsi", "oss", "pdk", version)
  def env_extra(self) -> dict[str, str]:
    return {"PDK" : self.version}


