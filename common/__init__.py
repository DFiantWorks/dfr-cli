import subprocess
import shlex
import os
import time
import sys
import importlib
import requests
import re
from typing import Dict
from abc import abstractmethod
import stat


class Paths:
    TOOLS = "/mnt/tools"
    INSTALL = f"{TOOLS}/install"
    SCRIPTS = f"{TOOLS}/scripts"
    STAGING = f"{TOOLS}/staging"
    COMMON_SCRIPTS = f"{SCRIPTS}/common"


paths = Paths()


def addEnvPaths(envName: str, paths: list[str]) -> None:
    if len(os.environ.get(envName, "")) == 0:
        os.environ[envName] = ":".join(paths)
    else:
        os.environ[envName] = f"{os.environ[envName]}:{':'.join(paths)}"


def downloadAvailable(url: str) -> bool:
    return requests.head(url).status_code < 400


def wildcardToRegex(pattern: str) -> re.Pattern:
    return re.compile("^" + re.escape(pattern).replace("\\*", ".*").replace("\\?", ".") + "$")


def isCommitVersion(version: str) -> bool:
    return re.fullmatch(r"^[0-9a-fA-F]$", version or "") is not None and len(version) >= 5


def getNewestVersionFolder(path: str, pattern: re.Pattern) -> str:
    # from listing of all the given path file/folders that fall within
    # the given pattern
    fileOrFolderList: list[str] = list(filter(lambda x: re.match(pattern, x) is not None, os.listdir(path)))
    folderList: list[str] = list(
        filter(
            # filtering just folders
            os.path.isdir,
            # creating full paths for directory check
            map(lambda x: os.path.join(path, x), fileOrFolderList),
        )
    )
    if folderList:
        return os.path.basename(max(folderList, key=lambda x: os.stat(x).st_ctime_ns))
    else:
        return ""


class Tool:
    domain: str
    vendor: str
    name: str
    version: str

    def __init__(self, domain: str, vendor: str, name: str, versionReq: str):
        self.domain = domain
        self.vendor = vendor
        self.name = name
        self.version = self.actualVersion(versionReq)

    def actualVersion(self, versionReq: str) -> str:
        return versionReq

    def dependencies(self) -> list[str]:
        return []

    def fullName(self) -> str:
        return f"{self.domain}.{self.vendor}.{self.name}"

    def install(self, flags: str):
        if os.path.exists(self.installPath()):
            print(f"Tool folder for {self.fullName()} with version {self.version} already exists.")
            sys.exit(1)

    def installPath(self) -> str:
        return f"{paths.INSTALL}/{self.domain}/{self.vendor}/{self.name}/{self.version}"

    def linkedPath(self) -> str:
        return f"/opt/{self.name}"

    def execFolder(self) -> str:
        return "bin"

    # command aliases to be created [<origin path> : <alias name>]
    # by default, empty list
    def cmdAliases(self) -> list[tuple[str, str]]:
        return []

    # symbolic links to be created [<origin path> : <link path>]
    # by default, adding a link between install path and the defined linked path
    def symlinks(self) -> list[tuple[str, str]]:
        return [(self.installPath(), self.linkedPath())]

    # added paths to the path environment variable
    # by default, adding the execution path as determined by the linked path and execution folder
    def env_path(self) -> list[str]:
        return [f"{self.linkedPath()}/{self.execFolder()}"]

    # added python paths to the python path environment variable
    # by default, empty list
    def env_python_path(self) -> list[str]:
        return []

    # added ld_library paths to the ld_library path environment variable
    # by default, empty list
    def env_ld_library_path(self) -> list[str]:
        return []

    # added man paths to the man path environment variable
    # by default, empty list
    def env_man_path(self) -> list[str]:
        return []

    # added pkg_config paths to the pkg_config path environment variable
    # by default, empty list
    def env_pkg_config_path(self) -> list[str]:
        return []

    # added other environment variables {<var_name> : <value>, ...}
    # by default, empty dict
    def env_extra(self) -> dict[str, str]:
        return {}

    # the initial environment setup that includes environment variables,
    # symlinks, and command aliases
    def setup_env(self):
        addEnvPaths("PATH", self.env_path())
        addEnvPaths("PYTHONPATH", self.env_python_path())
        addEnvPaths("LD_LIBRARY_PATH", self.env_ld_library_path())
        addEnvPaths("MANPATH", self.env_man_path())
        addEnvPaths("PKG_CONFIG_PATH", self.env_pkg_config_path())
        for env in self.env_extra().items():
            os.environ[env[0]] = env[1]
        for symlink in self.symlinks():
            os.symlink(symlink[0], symlink[1])
        for cmdAlias in self.cmdAliases():
            with open(f"/usr/bin/{cmdAlias[1]}", "w") as f:
                f.write("#!/bin/bash\n")
                f.write(f'{cmdAlias[0]} "$@"')
            os.chmod(f"/usr/bin/{cmdAlias[1]}", 0o777)


def getTool(fullName: str, versionReq: str) -> Tool:
    if fullName.count(".") != 2:
        print(f"Expected full name in format <domain>.<vendor>.<name>, but found: {fullName}")
        sys.exit(1)
    try:
        module = importlib.import_module(f"dfr_scripts.{fullName}")
        return module.SpecificTool(versionReq)
    except ModuleNotFoundError as e:
        print(f"Missing install script for `{fullName}`")
        sys.exit(1)


class Tools:
    all: dict[str, Tool] = {}

    def __init__(self, tool_versions_flat: dict[str, str]):
        for fullName, versionReq in tool_versions_flat.items():
            self.all[fullName] = getTool(fullName, versionReq)

    def setup_env(self):
        for t in self.all.items():
            t[1].setup_env()


class ZeroInstallTool(Tool):
    def install(self, flags: str):
        pass

    def symlinks(self) -> list[tuple[str, str]]:
        return []

    def env_path(self) -> list[str]:
        return []


class ShellInstallTool(Tool):
    @abstractmethod
    def installShellCmd(self, flags: str) -> str:
        pass

    def install(self, flags: str):
        super().install(flags)
        cmd = self.installShellCmd(flags)
        # strip empty lines (only whitespaces and newlines)
        properCmd = "".join([s.strip(" ") for s in cmd.splitlines(True) if s.strip("\t\r\n ")])
        r = subprocess.run(properCmd, shell=True)
        if r.returncode != 0:
            sys.exit(r.returncode)


class GitOSSTool(ShellInstallTool):
    def __init__(self, domain: str, name: str, versionReq: str, repo: str):
        super().__init__(domain, "oss", name, versionReq)
        self.repo = repo

    def buildAndInstallShellCmd(self, flags: str) -> str:
        return f"""
      echo Missing build & install command override for {self.fullName()}.
      exit 1
    """

    def installShellCmd(self, flags: str) -> str:
        return f"""
      set -e
      cd /tmp
      git clone {self.repo} {self.name}
      cd {self.name}
      git checkout {self.version}
      TIMEDATE=`TZ=UTC0 git show --quiet --date='format-local:%Y%m%d%H%M.%S' --format="%cd"`
      {self.buildAndInstallShellCmd(flags)}
      touch -a -m -t $TIMEDATE {self.installPath()}
    """


class InteractivelyDownloadedTool(Tool):
    def __init__(self, domain: str, vendor: str, name: str, versionReq: str):
        super().__init__(domain, vendor, name, versionReq)

    # all firefox downloads will be automatically placed here
    downloadsPath = "~/Downloads"

    @abstractmethod
    def downloadFileName(self) -> str:
        pass

    def downloadedFilePath(self) -> str:
        return f"{self.downloadsPath}{self.downloadFileName()}"

    @abstractmethod
    def downloadURL(self) -> str:
        pass

    @abstractmethod
    def downloadInstructions(self) -> str:
        pass

    def unsupportedVersionErr(self):
        print(f"Error: {self.name} version `{self.version}` is not supported.")
        sys.exit(1)

    def install(self, flags: str):
        print(f"(Remote) Firefox is now opening the {self.vendor} download page for you.")
        print(self.downloadInstructions())
        firefoxPid = subprocess.Popen(
            ["firefox", self.downloadURL()],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        downloadedFilePath = self.downloadedFilePath()
        print("Waiting for start of file download...")
        while not os.path.exists(downloadedFilePath):
            time.sleep(1)
        print("Start of download detected.")
        print("Waiting for end of download (do not close the firefox browser)...")
        while os.path.getsize(downloadedFilePath) == 0:
            time.sleep(1)
        print("Download completed!")
        firefoxPid.terminate()
        print("Extracting setup...")
        self.extract()

    def extract(self):
        pass


class XilinxTool(InteractivelyDownloadedTool):
    def __init__(self, name: str, versionReq: str):
        super().__init__("vlsi", "Xilinx", name, versionReq)

    @abstractmethod
    def versionToFileNameMap(self) -> Dict[str, str]:
        pass

    # TODO: consider replacing with webcrawling techniques instead of a fixed lookup
    def downloadFileName(self) -> str:
        try:
            return self.versionToFileNameMap()[self.version]
        except:
            return self.unsupportedVersionErr()

    def downloadURL(self) -> str:
        return f"https://www.xilinx.com/member/forms/download/xef.html?filename={self.downloadFileName()}"

    def downloadInstructions(self) -> str:
        return "Login with your Xilinx account and then click on the Download button at the bottom of the page."


class Vivado(XilinxTool):
    def __init__(self, versionReq: str):
        super().__init__("Vivado", versionReq)

    def versionToFileNameMap(self) -> Dict[str, str]:
        return {
            "2022.1": "Xilinx_Unified_2022.1_0420_0327_Lin64.bin",
            "2021.2": "Xilinx_Unified_2021.2_1021_0703_Lin64.bin",
            "2021.1": "Xilinx_Unified_2021.1_0610_2318_Lin64.bin",
            "2020.3": "Xilinx_Unified_2020.3_0407_2214_Lin64.bin",
            "2020.2": "Xilinx_Unified_2020.2_1118_1232_Lin64.bin",
            "2020.1": "Xilinx_Unified_2020.1_0602_1208_Lin64.bin",
        }

    def extract(self):
        downloadedFilePath = self.downloadedFilePath()
        os.chmod(downloadedFilePath, 0o777)
        subprocess.run(shlex.split(f"{downloadedFilePath} --keep --noexec --target {self.downloadsPath}"))
