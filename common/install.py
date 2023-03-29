from dfr_scripts.common import getTool
import sys
import shlex

tool_fullName, tool_version, toolMnt, *tool_flags = sys.argv[1:]
getTool(tool_fullName, tool_version).install(toolMnt, shlex.join(tool_flags))
