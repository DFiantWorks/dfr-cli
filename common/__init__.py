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
import fnmatch
from datetime import datetime
import git
from git import Repo, RemoteProgress
import shutil


class Paths:
    common = os.path.dirname(os.path.abspath(__file__))


paths = Paths()


# remove initial `v` character from a string when it is followed by either a
# digit, `*` or `?`.
def strip_initial_v(string):
    pattern = r"^v([\d*?].*)$"
    match = re.match(pattern, string)
    if match:
        return match.group(1)
    else:
        return string


def isPatternVersion(version: str) -> bool:
    return "*" in version or "?" in version


def isCommitVersion(version: str) -> bool:
    pattern = r"^[0-9a-fA-F]+$"
    return re.match(pattern, version) is not None and len(version) >= 6


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


def get_latest_commit_hash(repoOwnerName: str, repoName: str, branch: Optional[str] = None) -> str:
    if branch is None:
        branch = get_default_branch(repoOwnerName, repoName)
    api_url = f"https://api.github.com/repos/{repoOwnerName}/{repoName}/branches/{branch}"  # create the api url

    # make the request
    response = requests.get(api_url)

    # check for errors
    if response.status_code != 200:
        print(f"`{api_url}` error with status code: {response.status_code}")
        return sys.exit(1)

    # extract the latest commit hash
    branch_data = response.json()
    latest_commit_hash = branch_data["commit"]["sha"]

    return latest_commit_hash


def get_default_branch(repoOwnerName: str, repoName: str) -> str:
    api_url = f"https://api.github.com/repos/{repoOwnerName}/{repoName}"  # create the api url

    # make the request
    response = requests.get(api_url)

    # check for errors
    if response.status_code != 200:
        print(f"`{api_url}` error with status code: {response.status_code}")
        return sys.exit(1)

    # extract the default branch
    repo_data = response.json()
    default_branch = repo_data["default_branch"]

    return default_branch


def get_submodule_commit_hash(repoOwnerName: str, repoName: str, submodulePath: str, ref: str) -> Optional[str]:
    try:
        url = f"https://api.github.com/repos/{repoOwnerName}/{repoName}/contents/{submodulePath}?ref={ref}"
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


def get_commit_datetime(repoOwnerName: str, repoName: str, commit_hash: str) -> Optional[str]:
    api_url = f"https://api.github.com/repos/{repoOwnerName}/{repoName}/commits/{commit_hash}"  # create the api url
    # make the request
    response = requests.get(api_url)

    # if a commit is no longer available returning None
    if response.status_code == 422:
        return None

    # check for errors
    if response.status_code != 200:
        print(f"`{api_url}` error with status code: {response.status_code}")
        return sys.exit(1)

    # extract the commit datetime
    commit_data = response.json()
    commit_datetime = commit_data["commit"]["committer"]["date"]

    return commit_datetime


def sort_tags_by_commit_datetime(
    repoOwnerName: str, repoName: str, tags_commits_dict: dict[str, str]
) -> dict[str, str]:
    # step 1 and 2: get commit datetime for each commit and create a list of tuples
    tuples_list = []
    for tag, commit in tags_commits_dict.items():
        commit_datetime = get_commit_datetime(repoOwnerName, repoName, commit)
        if commit_datetime:
            tuples_list.append((tag, commit, commit_datetime))

    # step 3: sort the list of tuples by commit datetime
    tuples_list.sort(key=lambda x: datetime.fromisoformat(x[2].replace("Z", "")), reverse=True)

    # step 4: convert the list of tuples back into a dictionary
    sorted_dict = {t[0]: t[1] for t in tuples_list}

    return sorted_dict


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


# convert dfr-supported patterns to standard patterns
def dfrToStdPattern(pattern: str) -> str:
    if pattern == "latest":
        return "*"
    else:
        return pattern


def installDirReadyFile(path: str) -> str:
    return os.path.join(path, ".dfr_ready")


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


def getReadyFolders(path: str, __filterFunc: Callable[[str], bool]) -> list[str]:
    if not os.path.exists(path):
        return []
    # listing all the given path file/folders according to the given filter
    fileOrFolderList: list[str] = list(filter(__filterFunc, os.listdir(path)))
    return list(
        filter(
            # filtering just folders
            lambda x: os.path.isdir(x) and os.path.exists(installDirReadyFile(x)),
            # creating full paths for directory check
            map(lambda x: os.path.join(path, x), fileOrFolderList),
        )
    )


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
        self.versionReq = dfrToStdPattern(strip_initial_v(versionReq))

    def latestInstalledVersionFiltered(self, __filterFunc: Callable[[str], bool]) -> VersionLoc:
        # listing all the given path file/folders according to the given filter
        folderList: list[str] = (
            getReadyFolders(self._toolPathNoVersion("osstools"), __filterFunc)
            + getReadyFolders(self._toolPathNoVersion("orgtools"), __filterFunc)
            + getReadyFolders(self._toolPathNoVersion("mytools"), __filterFunc)
        )
        if folderList:
            fullPath = max(folderList, key=lambda x: os.stat(installDirReadyFile(x)).st_ctime_ns)
            toolMnt = fullPath.split("/")[2]
            return VersionLoc(toolMnt, os.path.basename(fullPath))
        else:
            return VersionLoc("", "")

    def latestInstallableVersion(self, pattern: str) -> str:
        return self.versionReq

    def latestInstalledVersion(self, pattern: str) -> VersionLoc:
        return self.latestInstalledVersionFiltered(lambda x: re.match(pattern, x) is not None)

    # def actualVersion(self, versionReq: str) -> VersionLoc:
    #     toolMnt = "mytools"
    #     # requests latest
    #     if isPatternVersion(versionReq):
    #         # has concrete version specified
    #         if ":" in versionReq:
    #             req, concrete = versionReq.split(":")
    #             return VersionLoc(toolMnt, concrete)
    #         else:
    #             return self.latestInstalledVersion(versionReq)
    #     else:
    #         return VersionLoc(toolMnt, versionReq)

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
        if version == "":
            print(
                f"No installable versions found to match the pattern `{self.versionReq}` for the tool `{self.fullName()}`"
            )
            sys.exit(1)
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
        self.versionLoc = self.latestInstalledVersion(self.versionReq)
        if self.versionLoc.version == "" or (not self._zero_install and not self.isInstalled()):
            print(
                f'Missing version that matches `{self.versionReq}`.\nConsider running: `dfr install {self.fullName()} "{self.versionReq}"`'
            )
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


class CloneProgress(RemoteProgress):
    def update(self, op_code, cur_count, max_count=None, message=""):
        percentage = (cur_count / max_count) * 100 if max_count else 0
        print(f"Progress: {percentage:.2f}%", end="\r")


class GitOSSTool(ShellInstallTool):
    repoURL: str
    repoOwnerName: str
    repoName: str
    repo: Optional[Repo] = None
    repoLocalPath: str
    # if set to true, then latest installable version will only cater to tagged commits
    _useOnlyTaggedCommits: bool = False

    def getRepo(self) -> Repo:
        if self.repo:
            return self.repo
        else:
            print(f"Cloning from {self.repoURL} ...")
            self.repoLocalPath = f"/tmp/dfr_git_{self.repoName}"
            shutil.rmtree(self.repoLocalPath, ignore_errors=True)
            self.repo = Repo.clone_from(self.repoURL, self.repoLocalPath, progress=CloneProgress())
            return self.repo

    def getLatestCommitHash(self) -> str:
        """Get the commit hash of the remote HEAD."""
        output = subprocess.check_output(["git", "ls-remote", self.repoURL, "HEAD"])
        return output.decode().split()[0]

    def getFullCommitHash(self, partial: str) -> str:
        if len(partial) == 40:
            return partial
        else:
            return self.getRepo().commit(partial).hexsha

    def __init__(self, domain: str, name: str, versionReq: str, repoURL: str):
        self.repoURL = repoURL
        self.repoOwnerName, self.repoName = extract_owner_and_repo_from_github_url(self.repoURL)
        super().__init__(domain, "oss", name, versionReq)

    @final
    def getGitSubmoduleCommit(self, submoduleName: str) -> Optional[str]:
        return get_submodule_commit_hash(self.repoOwnerName, self.repoName, submoduleName, self.versionLoc.version)

    # get a dict of tagged commits matching a given tag (unix name) pattern.
    # keys are tags, values are commits.
    @final
    def getGitTagCommits(self, tagPattern: str) -> dict[str, str]:
        command = f"git ls-remote -t {self.repoURL}"
        commitsTagsBytes = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE).stdout.read().splitlines()  # type: ignore
        ret: dict[str, str] = {}
        for ctb in commitsTagsBytes:
            commit, tag = ctb.decode("utf-8").replace("refs/tags/", "").split("\t")
            if fnmatch.fnmatch(strip_initial_v(tag), tagPattern):
                ret[tag] = commit
        return ret

    # the same as getGitTagCommits, but where the tags are ordered from newest to oldest commits
    @final
    def getGitOrderedTagCommits(self, tagPattern: str) -> dict[str, str]:
        tagsAndCommits = self.getGitTagCommits(tagPattern)
        if len(tagsAndCommits) <= 1:
            return tagsAndCommits
        else:
            return sort_tags_by_commit_datetime(self.repoOwnerName, self.repoName, self.getGitTagCommits(tagPattern))

    def latestInstalledVersion(self, versionReq: str) -> VersionLoc:
        commits: list[str]
        if isCommitVersion(versionReq):
            return self.latestInstalledVersionFiltered(lambda x: x.startswith(versionReq))
        elif versionReq == "*" and not self._useOnlyTaggedCommits:
            return self.latestInstalledVersionFiltered(lambda x: True)
        else:
            commits = list(self.getGitTagCommits(versionReq).values())
            return self.latestInstalledVersionFiltered(lambda x: x in commits)

    def latestInstallableVersion(self, versionReq: str) -> str:
        if isCommitVersion(versionReq):
            return self.getFullCommitHash(versionReq)
        elif versionReq == "*" and not self._useOnlyTaggedCommits:
            return self.getLatestCommitHash()
        else:
            commits = list(self.getGitOrderedTagCommits(versionReq).values())
            if commits:
                return commits[0]
            else:
                return ""

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
        self.getRepo().git.checkout(self.versionLoc.version)
        if self.recursiveClone():
            self.getRepo().submodule_update(recursive=True)
        # acceptErr = ""
        # if self.acceptCloneError():
        #     acceptErr = "|| true"
        return f"""
                sudo rm -rf {self.installPath()}
                sudo mkdir -p {self.installPath()}
                cd {self.repoLocalPath}
                TIMEDATE=`TZ=UTC0 git show --quiet --date='format-local:%Y%m%d%H%M.%S' --format="%cd"`
                {self.buildAndInstallShellCmd(flags)}
                sudo touch -a -m -t $TIMEDATE {self.installDirReadyFilePath()}
                sudo rm -rf {self.repoLocalPath}
                """


class GitPythonOSSTool(GitOSSTool):
    def __init__(self, domain: str, name: str, versionReq: str, repo: str):
        super().__init__(domain, name, versionReq, repo)

    def buildAndInstallShellCmd(self, flags: str) -> str:
        return f"""
                echo Copying source files into installation folder without git history...
                sudo rsync -a --info=progress2 . {self.installPath()} --exclude '.git'
                """

    # no paths for a python lib (we set python path)
    def env_path(self) -> list[str]:
        return []

    # add to python path
    def env_python_path(self) -> list[str]:
        return [f"{self.linkedPath()}/{self.execFolder()}"]


# class DownloadedTool(Tool):
#     def __init__(self, domain: str, vendor: str, name: str, versionReq: str):
#         super().__init__(domain, vendor, name, versionReq)

#     # all firefox downloads will be automatically placed here
#     downloadsPath = os.path.expanduser("~/Downloads")

#     @abstractmethod
#     def downloadFileName(self) -> str:
#         pass

#     def downloadedFilePath(self) -> str:
#         return f"{self.downloadsPath}/{self.downloadFileName()}"

#     @abstractmethod
#     def downloadURL(self) -> str:
#         pass

#     def unsupportedVersionErr(self):
#         print(f"Error: {self.name} version `{self.versionLoc.version}` is not supported.")
#         sys.exit(1)

#     def _install(self, flags: str):
#         downloadedFilePath = self.downloadedFilePath()
#         self._downloadWithFirefox(downloadedFilePath, self.downloadURL())
#         print("Extracting setup...")
#         self.extract()
#         os.remove(downloadedFilePath)
#         self.postDownloadInstall(flags)

#     def extract(self):
#         pass

#     def postDownloadInstall(self, flags: str):
#         pass


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

    def latestInstallableVersion(self, versionReq: str) -> str:
        for version in self.versionToFileNameMap().keys():
            if fnmatch.fnmatch(version, versionReq):
                return version
        return ""

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
