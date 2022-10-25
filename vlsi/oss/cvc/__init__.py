from dfr_scripts.common import Tool, GitOSSTool

def tool(version: str) -> Tool: 
  return GitOSSTool("vlsi", "cvc", version, "https://github.com/d-m-bailey/cvc")
