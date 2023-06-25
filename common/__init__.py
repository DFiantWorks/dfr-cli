import subprocess
import shlex
import os
import time
import sys
import importlib.util
import requests
import re
from typing import Dict, Optional
from abc import abstractmethod
from typing import final, Callable
import string
import stat
import os
import yaml
from collections import OrderedDict
import re
from urllib.parse import urlparse
import textwrap


class Paths:
    common = os.path.dirname(os.path.abspath(__file__))


paths = Paths()


def extract_owner_and_repo_from_github_url(github_url):
    parsed_url = urlparse(github_url)

    if parsed_url.netloc == "github.com":
        match = re.match(r"^/([^/]+)/([^/]+)", parsed_url.path)

        if match:
            owner, repo = match.groups()
            # Remove .git extension if present
            repo = re.sub(r"\.git$", "", repo)
            return owner, repo
        else:
            print("Invalid GitHub URL format.")
            return sys.exit(1)
    else:
        print("URL is not a GitHub URL.")
        return sys.exit(1)


def get_submodule_commit_hash(ownerName: str, repoName: str, submodulePath: str, ref: str) -> Optional[str]:
    try:
        url = f"https://api.github.com/repos/{ownerName}/{repoName}/contents/{submodulePath}?ref={ref}"
        response = requests.get(url)

        if response.status_code == 200:
            submodule_info = response.json()
            if submodule_info["type"] == "submodule":
                commit_hash = submodule_info["sha"]
                return commit_hash
            else:
                print("The specified path is not a submodule.")
                sys.exit(1)
        else:
            return None
    except Exception as e:
        print(f"Error while getting the submodule commit hash: {str(e)}")
        sys.exit(1)


def addEnvPaths(envName: str, paths: list[str]) -> None:
    if len(os.environ.get(envName, "")) == 0:
        os.environ[envName] = ":".join(paths)
    else:
        os.environ[envName] = f"{os.environ[envName]}:{':'.join(paths)}"


def getEnvPaths(envName: str, paths: list[str]) -> list[str]:
    if paths:
        return [f"export {envName}=${{{envName}:+${envName}:}}{':'.join(paths)}"]
    else:
        return []


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


class VersionLoc:
    toolMnt: str
    version: str

    def __init__(self, toolMnt: str, version: str):
        self.toolMnt = toolMnt
        self.version = version


class Tool:
    domain: str
    vendor: str
    name: str
    versionReq: str
    versionLoc: VersionLoc
    _zero_install: bool = False

    def __init__(self, domain: str, vendor: str, name: str, versionReq: str):
        self.domain = domain
        self.vendor = vendor
        self.name = name
        self.versionReq = versionReq

    def latestInstallableVersion(self, pattern: str) -> str:
        return self.versionReq

    def latestVersion(self, pattern: str) -> VersionLoc:
        toolMnt = "mytools"
        return VersionLoc(
            toolMnt,
            getNewestVersionFolder(
                self._toolPathNoVersion(toolMnt), lambda x: re.match(wildcardToRegex(pattern), x) is not None
            ),
        )

    def actualVersion(self, versionReq: str) -> VersionLoc:
        toolMnt = "mytools"
        # requests latest
        if "*" in versionReq or "?" in versionReq:
            # has concrete version specified
            if ":" in versionReq:
                req, concrete = versionReq.split(":")
                return VersionLoc(toolMnt, concrete)
            else:
                return self.latestVersion(versionReq)
        else:
            return VersionLoc(toolMnt, versionReq)

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
    def getInstalledToolMnt(self, version: str) -> Optional[str]:
        if os.path.exists(self.installDirReadyFilePath(toolMntOpt="osstools", versionOpt=version)):
            return "osstools"
        elif os.path.exists(self.installDirReadyFilePath(toolMntOpt="orgtools", versionOpt=version)):
            return "orgtools"
        elif os.path.exists(self.installDirReadyFilePath(toolMntOpt="mytools", versionOpt=version)):
            return "mytools"
        else:
            return None

    @final
    def isInstalled(self) -> bool:
        if self.getInstalledToolMnt(self.versionLoc.version):
            return True
        else:
            return False

    @final
    def installDependencies(self, toolMntReq: str):
        # if we have dependencies, we install them up as well
        for depFullName, depVersionReq in self.dependencies().items():
            getTool(depFullName, depVersionReq).install(toolMntReq, "", True)

    @final
    def install(self, toolMntReq: str, flags: str, withToolDeps: bool):
        version = self.latestInstallableVersion(self.versionReq)
        toolMnt: str
        installedToolMnt = self.getInstalledToolMnt(version)
        if installedToolMnt:
            toolMnt = installedToolMnt
        else:
            toolMnt = toolMntReq
        self.versionLoc = VersionLoc(toolMnt=toolMnt, version=version)
        if installedToolMnt:
            print(f"Found exiting tool `{self.fullName()}` with version `{version}` under mount `{toolMnt}`.")
        else:
            print(f"Installing tool `{self.fullName()}` with version `{version}` under mount `{toolMnt}`...")
            self._install(flags)
        if withToolDeps and self.dependencies():
            print(f"Installing tool dependencies of `{self.fullName()}`...")
            self.installDependencies(toolMntReq)

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

    def _toolPathNoVersion(self, toolMnt: str) -> str:
        return f"/mnt/{toolMnt}/{self.domain}/{self.vendor}/{self.name}"

    @final
    def installPath(self, toolMntOpt: Optional[str] = None, versionOpt: Optional[str] = None) -> str:
        toolMnt: str
        if toolMntOpt:
            toolMnt = toolMntOpt
        else:
            toolMnt = self.versionLoc.toolMnt
        version: str
        if versionOpt:
            version = versionOpt
        else:
            version = self.versionLoc.version
        return f"{self._toolPathNoVersion(toolMnt)}/{version}"

    @final
    def installDirReadyFilePath(self, toolMntOpt: Optional[str] = None, versionOpt: Optional[str] = None) -> str:
        return installDirReadyFile(self.installPath(toolMntOpt=toolMntOpt, versionOpt=versionOpt))

    def linkedPath(self) -> str:
        return f"/opt/{self.name}"

    def execFolder(self) -> str:
        return "bin"

    # command aliases to be created [<alias name> : <origin path>]
    # by default, empty dict
    def cmdAliases(self) -> dict[str, str]:
        return {}

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

    # environment source files to add with bash `source`
    # by default, empty list
    def env_sources(self) -> list[str]:
        return []

    # added other environment variables {<var_name> : <value>, ...}
    # by default, empty dict
    def env_extra(self) -> dict[str, str]:
        return {}

    # additional commands for environment setup
    # by default, empty list
    def env_extra_cmds(self) -> list[str]:
        return []

    def setVersion(self):
        self.versionLoc = self.actualVersion(self.versionReq)
        if self.versionLoc.version == "" or (not self._zero_install and not self.isInstalled()):
            print(f"Missing version. Consider running: `dfr install {self.fullName()} {self.versionReq}`")
            sys.exit(1)

    # the initial environment setup that includes environment variables,
    # symlinks, and command aliases
    @final
    def getEnv(self) -> list[str]:
        self.setVersion()
        for symlink in self.symlinks():
            os.symlink(symlink[0], symlink[1])
        return (
            [f"#Environment for {self.name}"]
            + getEnvPaths("PATH", self.env_path())
            + getEnvPaths("PYTHONPATH", self.env_python_path())
            + getEnvPaths("LD_LIBRARY_PATH", self.env_ld_library_path())
            + getEnvPaths("MANPATH", self.env_man_path())
            + getEnvPaths("PKG_CONFIG_PATH", self.env_pkg_config_path())
            + list(map(lambda e: f"export {e[0]}={e[1]}", self.env_extra().items()))
            + list(map(lambda a: f"alias {a[0]}={a[1]}", self.cmdAliases().items()))
            + list(map(lambda s: f"source {s}", self.env_sources()))
            + self.env_extra_cmds()
        )


def getToolModule(fullName: str):
    try:
        module_name = f"dfr_scripts.{fullName}"
        spec = importlib.util.spec_from_file_location(
            module_name, f"/etc/dfr/dfr_scripts/{fullName.replace('.','/')}/__init__.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    except FileNotFoundError:
        print(f"Missing script for `{fullName}`")
        sys.exit(1)


def getTool(fullName: str, versionReq: str) -> Tool:
    module = getToolModule(fullName)
    return module.SpecificTool(versionReq)


def getDependencies(fullName: str) -> set[str]:
    try:
        module = getToolModule(fullName)
        return module.dependencies
    except AttributeError:
        return set()


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

    def getEnv(self) -> list[str]:
        totalEnv: list[str] = []
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
            totalEnv = totalEnv + tool.getEnv()
            setTools.add(tool.fullName())
            # if we have dependencies, we set them up as well
            for depFullName, depVersionReq in tool.dependencies().items():
                if depFullName not in setTools:
                    tools = [getTool(depFullName, depVersionReq)] + tools
        return totalEnv


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

    @final
    def getGitSubmoduleCommit(self, submoduleName: str) -> Optional[str]:
        ownerName, repoName = extract_owner_and_repo_from_github_url(self.repo)
        return get_submodule_commit_hash(ownerName, repoName, submoduleName, self.versionLoc.version)

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

    def latestVersion(self, pattern: str) -> VersionLoc:
        toolMnt = "mytools"
        commits = self.getGitTagPatternCommits(wildcardToRegex(pattern))
        return VersionLoc(toolMnt, getNewestVersionFolder(self._toolPathNoVersion(toolMnt), lambda x: x in commits))

    def latestInstallableVersion(self, version: str) -> str:
        if isCommitVersion(version) and not self._useTags:
            if len(version) == 40:
                return version  # full commit
            else:  # find full version
                return self.getGitFullCommit(version)
        else:
            return self.getGitTagPatternCommits(wildcardToRegex(version)).pop()

    def actualVersion(self, versionReq: str) -> VersionLoc:
        toolMnt = "mytools"
        versionLoc = super().actualVersion(versionReq)
        if isCommitVersion(versionLoc.version) and not self._useTags:
            if len(versionLoc.version) == 40:
                return versionLoc  # full commit
            else:  # find full version
                return VersionLoc(
                    toolMnt,
                    getNewestVersionFolder(self._toolPathNoVersion(toolMnt), lambda x: x.startswith(versionReq)),
                )
        else:
            return self.latestVersion(versionLoc.version)

    def buildAndInstallShellCmd(self, flags: str) -> str:
        return f"""
                echo Missing build & install command override for {self.fullName()}.
                exit 1
                """

    def recursiveClone(self) -> bool:
        return False

    def acceptCloneError(self) -> bool:
        return False

    @final
    def _installShellCmd(self, flags: str) -> str:
        recursiveFlag = ""
        recursiveCheckout = ""
        if self.recursiveClone():
            recursiveFlag = "--recursive"
            recursiveCheckout = "git submodule update --init --recursive"
        acceptErr = ""
        if self.acceptCloneError():
            acceptErr = "|| true"
        return f"""
                sudo rm -rf {self.installPath()}
                sudo mkdir -p {self.installPath()}
                sudo rm -rf /tmp/{self.name}
                cd /tmp
                git clone {recursiveFlag} {self.repo} {self.name} {acceptErr}
                cd {self.name}
                git checkout {self.versionLoc.version}
                {recursiveCheckout}
                TIMEDATE=`TZ=UTC0 git show --quiet --date='format-local:%Y%m%d%H%M.%S' --format="%cd"`
                {self.buildAndInstallShellCmd(flags)}
                sudo touch -a -m -t $TIMEDATE {self.installDirReadyFilePath()}
                sudo rm -rf /tmp/{self.name}
                """


class InteractivelyDownloadedTool(Tool):
    def __init__(self, domain: str, vendor: str, name: str, versionReq: str):
        super().__init__(domain, vendor, name, versionReq)

    # all firefox downloads will be automatically placed here
    downloadsPath = os.path.expanduser("~/Downloads")

    @abstractmethod
    def downloadFileName(self) -> str:
        pass

    def downloadedFilePath(self) -> str:
        return f"{self.downloadsPath}/{self.downloadFileName()}"

    @abstractmethod
    def downloadURL(self) -> str:
        pass

    @abstractmethod
    def downloadInstructions(self) -> str:
        pass

    def unsupportedVersionErr(self):
        print(f"Error: {self.name} version `{self.versionLoc.version}` is not supported.")
        sys.exit(1)

    def _downloadWithFirefox(self, downloadedFilePath: str, downloadURL: str):
        if os.path.exists(downloadedFilePath) and os.path.getsize(downloadedFilePath) != 0:
            print(f"Installation already downloaded.")
        else:
            print(f"(Remote) Firefox is now opening the {self.vendor} download page for you.")
            print(self.downloadInstructions())
            firefoxPid = subprocess.Popen(
                ["firefox", downloadURL],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if os.path.exists(downloadedFilePath):
                os.remove(downloadedFilePath)
            print(f"Waiting for start of file download at {downloadedFilePath}...")
            while not os.path.exists(downloadedFilePath):
                time.sleep(1)
            print("Start of download detected.")
            print("Waiting for end of download (do not close the firefox browser)...")
            while os.path.getsize(downloadedFilePath) == 0:
                time.sleep(1)
            print("Download completed!")
            firefoxPid.terminate()

    def _install(self, flags: str):
        downloadedFilePath = self.downloadedFilePath()
        self._downloadWithFirefox(downloadedFilePath, self.downloadURL())
        print("Extracting setup...")
        self.extract()
        os.remove(downloadedFilePath)
        self.postDownloadInstall(flags)

    def extract(self):
        pass

    def postDownloadInstall(self, flags: str):
        pass


class AMDTool(InteractivelyDownloadedTool):
    def __init__(self, name: str, versionReq: str):
        super().__init__("vlsi", "amd", name, versionReq)

    @abstractmethod
    def versionToFileNameMap(self) -> Dict[str, str]:
        pass

    # def latestInstallableVersion(self, pattern: str) -> str:
    #     return next(iter(self.versionToFileNameMap()))

    # TODO: consider replacing with webcrawling techniques instead of a fixed lookup
    def downloadFileName(self) -> str:
        try:
            return self.versionToFileNameMap()[self.versionLoc.version]
        except:
            return self.unsupportedVersionErr()

    def downloadURL(self) -> str:
        return f"https://www.xilinx.com/member/forms/download/xef.html?filename={self.downloadFileName()}"

    def downloadInstructions(self) -> str:
        return "Login with your Xilinx account and then click on the Download button at the bottom of the page."
