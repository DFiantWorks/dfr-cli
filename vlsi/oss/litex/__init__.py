from dfr_scripts.common import GitPythonOSSTool, isCommitVersion
import ast


class SpecificTool(GitPythonOSSTool):
    def __init__(self, versionReq: str):
        super().__init__("vlsi", "litex", versionReq, "https://github.com/enjoy-digital/litex")

    def dependencies(self) -> dict[str, str]:
        if isCommitVersion(self.versionReq):
            tag = "latest"
        else:
            tag = self.versionReq
        setupFile = f"{self.installPath()}/litex_setup.py"
        with open(setupFile, "r") as file:
            module = ast.parse(file.read())
        dictAST: ast.Dict
        for node in module.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if target.id == "git_repos":  # type: ignore
                        dictAST = node.value  # type: ignore
                        break
        ret: dict[str, str] = {}
        for key, value in zip(dictAST.keys, dictAST.values):
            if isinstance(value, ast.Call):
                dependency = f'vlsi.oss.{key.s.replace("-", "_")}'  # type: ignore
                if dependency != "vlsi.oss.litex":
                    for kw in value.keywords:
                        if kw.arg == "sha1":
                            ret[dependency] = hex(kw.value.n)[2:]  # type: ignore
                        elif kw.arg == "branch":
                            ret[dependency] = kw.value.s  # type: ignore
                        elif kw.arg == "tag":
                            ret[dependency] = tag
                        else:
                            ret[dependency] = "latest"
        return ret
