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
from typing import final, Callable
import string
import stat
import os
import yaml
from collections import OrderedDict


class Paths:
    TOOLS = "/mnt/tools"
    ORGTOOLS = "/mnt/orgtools"
    INSTALL = f"{TOOLS}"
    common = os.path.dirname(os.path.abspath(__file__))


paths = Paths()


def addEnvPaths(envName: str, paths: list[str]) -> None:
    if len(os.environ.get(envName, "")) == 0:
        os.environ[envName] = ":".join(paths)
    else:
        os.environ[envName] = f"{os.environ[envName]}:{':'.join(paths)}"


def downloadAvailable(url: str) -> bool:
    return requests.head(url).status_code < 400


def wildcardToRegex(pattern: str) -> re.Pattern:
    if pattern == "latest":
        return re.compile("^.*$")
    else:
        return re.compile("^" + re.escape(pattern).replace("\\*", ".*").replace("\\?", ".") + "$")


def installDirReadyFile(path: str) -> str:
    return os.path.join(path, ".dfr_ready")


def getNewestVersionFolder(path: str, __filterFunc: Callable[[str], bool]) -> str:
    if not os.path.exists(path):
        return ""
    # listing all the given path file/folders according to the given filter
    fileOrFolderList: list[str] = list(filter(__filterFunc, os.listdir(path)))
    folderList: list[str] = list(
        filter(
            # filtering just folders
            lambda x: os.path.isdir(x) and os.path.exists(installDirReadyFile(x)),
            # creating full paths for directory check
            map(lambda x: os.path.join(path, x), fileOrFolderList),
        )
    )
    if folderList:
        return os.path.basename(max(folderList, key=lambda x: os.stat(installDirReadyFile(x)).st_ctime_ns))
    else:
        return ""


def isCommitVersion(versionReq: str) -> bool:
    return all(c in string.hexdigits for c in versionReq) and len(versionReq) >= 5


def curlGitFolderCmd(repo: str, commit: str, folder: str) -> str:
    return f"curl -L {repo}/tarball/{commit}  | tar --wildcards */{folder} --strip-components={folder.count('/') + 2} -xzC ."


def runShellCmd(cmd: str):
    withErrCmd = f"""
                  set -e
                  {cmd}
                  """
    # strip empty lines (only whitespaces and newlines)
    properCmd = "".join([s.strip(" ") for s in withErrCmd.splitlines(True) if s.strip("\t\r\n ")])
    r = subprocess.run(properCmd, shell=True)
    if r.returncode != 0:
        sys.exit(r.returncode)


class Tool:
    domain: str
    vendor: str
    name: str
    versionReq: str
    version: str
    _zero_install: bool = False

    def __init__(self, domain: str, vendor: str, name: str, versionReq: str):
        self.domain = domain
        self.vendor = vendor
        self.name = name
        self.versionReq = versionReq

    def latestInstallableVersion(self, pattern: str) -> str:
        return self.versionReq

    def latestVersion(self, pattern: str) -> str:
        return getNewestVersionFolder(
            self.toolPathNoVersion(), lambda x: re.match(wildcardToRegex(pattern), x) is not None
        )

    def actualVersion(self, versionReq: str) -> str:
        # requests latest
        if "*" in versionReq or "?" in versionReq:
            # has concrete version specified
            if ":" in versionReq:
                req, concrete = versionReq.split(":")
                return concrete
            else:
                return self.latestVersion(versionReq)
        else:
            return versionReq

    def dependencies(self) -> dict[str, str]:
        return {}

    def siblings(self) -> set[str]:
        return set()

    @final
    def fullName(self) -> str:
        return f"{self.domain}.{self.vendor}.{self.name}"

    @abstractmethod
    def _install(self, flags: str):
        pass

    @final
    def install(self, flags: str):
        self.version = self.latestInstallableVersion(self.versionReq)
        if os.path.exists(self.installDirReadyFilePath()):
            print(f"Tool folder for {self.fullName()} with version {self.version} already exists.")
            sys.exit(1)
        self._install(flags)

    @final
    def _noDemoErr(self):
        print(f"No demo available for {self.fullName()}")
        sys.exit(1)

    def _demoAsk(self) -> str:
        return self._noDemoErr()

    def _demo(self, flags: str):
        self._noDemoErr()

    @final
    def demo(self, flags: str):
        self.setVersion()
        checkedFlags = flags
        if flags == "":
            checkedFlags = self._demoAsk()
        self._demo(checkedFlags)

    def toolPathNoVersion(self) -> str:
        return f"{paths.INSTALL}/{self.domain}/{self.vendor}/{self.name}"

    def installPath(self) -> str:
        return f"{self.toolPathNoVersion()}/{self.version}"

    def installDirReadyFilePath(self) -> str:
        return installDirReadyFile(self.installPath())

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

    # additional command to run after the rest of environment is set
    def env_final_run(self) -> str:
        return ""

    def setVersion(self):
        self.version = self.actualVersion(self.versionReq)
        if self.version == "" or (not self._zero_install and not os.path.exists(self.installDirReadyFilePath())):
            print(f"Missing version. Consider running: `dfr install {self.fullName()} {self.versionReq}`")
            sys.exit(1)

    # the initial environment setup that includes environment variables,
    # symlinks, and command aliases
    @final
    def setup_env(self):
        self.setVersion()
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
        cmd = self.env_final_run()
        if cmd != "":
            runShellCmd(cmd)


def getTool(fullName: str, versionReq: str) -> Tool:
    try:
        module = importlib.import_module(f"dfr_scripts.{fullName}")
        return module.SpecificTool(versionReq)
    except ModuleNotFoundError as e:
        print(f"Missing script for `{fullName}`")
        sys.exit(1)


def getDependencies(fullName: str) -> set[str]:
    try:
        module = importlib.import_module(f"dfr_scripts.{fullName}")
        return module.dependencies
    except AttributeError as e:
        return set()
    except ModuleNotFoundError as e:
        print(f"Missing script for `{fullName}`")
        sys.exit(1)


class Tools:
    all: OrderedDict[str, Tool] = OrderedDict()

    def __init__(self, tool_versions_flat: dict[str, str]):
        # ordering tools so that if a tool appears as another tool's dependency,
        # but also as standalone, the standalone will come first and take precedence
        ordered: list[str] = []
        toolNames: list[str] = list(tool_versions_flat.keys())
        while toolNames:
            head, *tail = toolNames
            deps: set[str] = getDependencies(head)
            if deps:
                goFirst = deps.intersection(toolNames)
                if goFirst:
                    toolNames = list(goFirst) + list(set(toolNames) - goFirst)
                else:
                    ordered.append(head)
                    toolNames = tail
            else:
                ordered.append(head)
                toolNames = tail
        for fullName in ordered:
            self.all[fullName] = getTool(fullName, tool_versions_flat[fullName])

    def setup_env(self):
        setTools: set[str] = set()
        tools: list[Tool] = list(self.all.values())
        while tools:
            tool, *tail = tools
            tools = tail
            # verifying existence of sibling configuration
            for s in tool.siblings():
                if s not in self.all:
                    print(f"Error: The tool {tool.fullName()} requires {s} configuration as well!")
                    sys.exit(1)
            tool.setup_env()
            setTools.add(tool.fullName())
            # if we have dependencies, we set them up as well
            for depFullName, depVersionReq in tool.dependencies().items():
                if depFullName not in setTools:
                    tools = [getTool(depFullName, depVersionReq)] + tools


class ZeroInstallTool(Tool):
    _zero_install: bool = True

    def _install(self, flags: str):
        pass

    def symlinks(self) -> list[tuple[str, str]]:
        return []

    def env_path(self) -> list[str]:
        return []


class ShellInstallTool(Tool):
    @abstractmethod
    def _installShellCmd(self, flags: str) -> str:
        pass

    @final
    def _install(self, flags: str):
        runShellCmd(self._installShellCmd(flags))


class GitOSSTool(ShellInstallTool):
    repo: str
    _useTags: bool = False

    def __init__(self, domain: str, name: str, versionReq: str, repo: str):
        self.repo = repo
        super().__init__(domain, "oss", name, versionReq)

    # get a set of commits or tags matching a given tag pattern.
    # if `retTags` is true then returning tags, otherwise returning commits
    @final
    def getGitTagPatternCommits(self, tagPattern: re.Pattern) -> set[str]:
        command = f"git ls-remote -t {self.repo}"
        commitsTagsBytes = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE).stdout.read().splitlines()  # type: ignore
        ret: set[str] = set()
        for ctb in commitsTagsBytes:
            commit, tag = ctb.decode("utf-8").replace("refs/tags/", "").split("\t")
            if re.match(tagPattern, tag) is not None:
                if self._useTags:
                    ret.add(tag)
                else:
                    ret.add(commit)
        return ret

    @final
    def getGitFullCommit(self, partialCommit: str) -> str:
        command = f"git ls-remote {self.repo}"
        commitsTagsBytes = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE).stdout.read().splitlines()  # type: ignore
        for ctb in commitsTagsBytes:
            commit: str = ctb.decode("utf-8").split("\t")[0]
            if commit.startswith(partialCommit):
                return commit
        return ""

    def latestVersion(self, pattern: str) -> str:
        commits = self.getGitTagPatternCommits(wildcardToRegex(pattern))
        return getNewestVersionFolder(self.toolPathNoVersion(), lambda x: x in commits)

    def latestInstallableVersion(self, version: str) -> str:
        if isCommitVersion(version) and not self._useTags:
            if len(version) == 40:
                return version  # full commit
            else:  # find full version
                return self.getGitFullCommit(version)
        else:
            return self.getGitTagPatternCommits(wildcardToRegex(version)).pop()

    def actualVersion(self, versionReq: str) -> str:
        version = super().actualVersion(versionReq)
        if isCommitVersion(version) and not self._useTags:
            if len(version) == 40:
                return version  # full commit
            else:  # find full version
                return getNewestVersionFolder(self.toolPathNoVersion(), lambda x: x.startswith(versionReq))
        else:
            return self.latestVersion(version)

    def buildAndInstallShellCmd(self, flags: str) -> str:
        return f"""
                echo Missing build & install command override for {self.fullName()}.
                exit 1
                """

    @final
    def _installShellCmd(self, flags: str) -> str:
        return f"""
                rm -rf {self.installPath()}
                cd /tmp
                git clone {self.repo} {self.name}
                cd {self.name}
                git checkout {self.version}
                TIMEDATE=`TZ=UTC0 git show --quiet --date='format-local:%Y%m%d%H%M.%S' --format="%cd"`
                {self.buildAndInstallShellCmd(flags)}
                touch -a -m -t $TIMEDATE {self.installDirReadyFilePath()}
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

    def _install(self, flags: str):
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
