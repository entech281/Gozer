import subprocess
import asyncio
REPO_PATH='c:/users/davec/gitwork/Robot2023/'

log_pane = None

def set_log_pane(d):
   global log_pane
   log_pane = d

def list_branches() -> list:
    branch_list_result=subprocess.run(['git','branch', '-l','--format',' %(refname)' ], cwd=REPO_PATH, capture_output=True,shell=True,check=False)
    if branch_list_result.returncode == 0:
        bl = branch_list_result.stdout.decode().split()
        bl_without_stuff = []
        for b in bl:
            v = b.replace('refs/heads/','')
            bl_without_stuff.append(v)
        return bl_without_stuff
    else:
        return []

def run_checkout(ref: str) -> str:
    log_pane.push("Pulling From Remote ".format(ref=ref))
    fetch_result = subprocess.run(['git', 'fetch', '--all'], cwd=REPO_PATH, capture_output=True, shell=True,check=False)
    if fetch_result.returncode != 0:
        log_pane.push(fetch_result.stderr.decode())
        return
    else:
        log_pane.push(fetch_result.stdout.decode())

    log_pane.push("Refreshing Branches...".format(ref=ref))
    BRANCH_LIST = list_branches()

    log_pane.push("Checking out ref '{ref}'".format(ref=ref))
    checkout_result=subprocess.run(['git','checkout', '-f', ref], cwd=REPO_PATH, capture_output=True,shell=True,check=False)
    git_hash=None
    if checkout_result.returncode == 0:
        revparse = subprocess.run(['git','rev-parse','--short','HEAD'], cwd=REPO_PATH, capture_output=True)
        git_hash = revparse.stdout.decode()

        log_pane.push("Done '{ref}'=={git_hash}".format(ref=ref, git_hash=git_hash))
    else:
        log_pane.push("ERROR: {error}".format(error=checkout_result.stderr.decode()))
    return git_hash

async def run_command(command: str) -> None:
    """Run a command in the background and display the output in the pre-created dialog."""
    process = await asyncio.create_subprocess_shell(command,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        cwd=REPO_PATH
    )
    # NOTE we need to read the output in chunks, otherwise the process will block
    output = ''
    while True:
        new = await process.stdout.read(200)
        if not new:
            break
        output = new.decode()
        # NOTE the content of the markdown element is replaced every time we have new output
        log_pane.push(output)