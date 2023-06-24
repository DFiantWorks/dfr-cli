from dfr_scripts.common import GitOSSTool


class SpecificTool(GitOSSTool):
    def __init__(self, versionReq: str):
        super().__init__("vlsi", "qflow", versionReq, "https://github.com/RTimothyEdwards/qflow")

    def buildAndInstallShellCmd(self, flags: str) -> str:
        return f"""
                ./configure
                cd src
                make vlog2Verilog && make vlog2Spice
                sudo mkdir -p {self.installPath()}/bin
                sudo cp vlog2Verilog {self.installPath()}/bin/
                sudo cp vlog2Spice {self.installPath()}/bin/
                cd ../scripts
                make spi2xspice.py
                chmod +x spi2xspice.py
                sudo cp spi2xspice.py {self.installPath()}/bin/
                """
