import subprocess
import asyncio
import configparser
import os.path
import logging

log_pane = None
REPO_PATH=None
CONFIG_FILE= "gozer.ini"

config=configparser.ConfigParser()
config.read(CONFIG_FILE)
path_to_try=config['DEFAULT']['repo_path']

if not path_to_try:
    raise ValueError("Can't find gozer.ini.sample. expecting it alongside the source in the git project")

if not os.path.exists(path_to_try):
    raise ValueError("Path '{s}' Does not appear to be valid in gozer.ini.sample".format(s=path_to_try))

REPO_PATH = path_to_try
DEPLOY_ENABLED = (config['DEFAULT']['enable_deploy'].lower() in ['true', '1', 't', 'y', 'yes'])

logging.info("Repository Path: ", REPO_PATH)
logging.info("Deploys Enabled:", DEPLOY_ENABLED)


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

async def run_deploy() -> bool:
    log_pane.push("Running Gradle Build...")
    await run_command('gradlew build')
    logging.info("Running Gradle Build")
    if DEPLOY_ENABLED:
        log_pane.push("Running Gradle Deploy...")
        successful_deploy = await run_command('gradlew deploy')
    else:
        successful_deploy = False
        log_pane.push("Not Deploying: Deploys are disabled")

    logging.info("Deploy Success:")
    return successful_deploy

def run_checkout(ref: str) -> str:
    log_pane.push("Pulling From Remote ".format(ref=ref))
    logging.info("Pulling from remote...")
    fetch_result = subprocess.run(['git', 'fetch', '--all'], cwd=REPO_PATH, capture_output=True, shell=True,check=False)
    if fetch_result.returncode != 0:
        log_pane.push(fetch_result.stderr.decode())
        return
    else:
        log_pane.push(fetch_result.stdout.decode())

    logging.info("Refreshing Branches...")
    log_pane.push("Refreshing Branches...".format(ref=ref))
    BRANCH_LIST = list_branches()

    logging.info("Checking out ref '{ref}'".format(ref=ref))
    log_pane.push("Checking out ref '{ref}'".format(ref=ref))
    checkout_result=subprocess.run(['git','checkout', '-f', ref], cwd=REPO_PATH, capture_output=True,shell=True,check=False)
    git_hash=None
    if checkout_result.returncode == 0:
        logging.info("Running git rev-parse --short HEAD")
        revparse = subprocess.run(['git','rev-parse','--short','HEAD'], cwd=REPO_PATH, capture_output=True)
        git_hash = revparse.stdout.decode()

        log_pane.push("Done '{ref}'=={git_hash}".format(ref=ref, git_hash=git_hash))
    else:
        log_pane.push("ERROR: {error}".format(error=checkout_result.stderr.decode()))
    return git_hash

async def run_command(command: str) -> bool:
    """Run a command in the background and display the output in the pre-created dialog."""
    logging.info("running command {s}".format(s=command))
    process = await asyncio.create_subprocess_shell(command,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        cwd=REPO_PATH
    )
    # NOTE we need to read the output in chunks, otherwise the process will block
    output = ''
    total_output=''
    while True:
        new = await process.stdout.read(200)
        if not new:
            break
        output = new.decode()
        total_output += output
        # NOTE the content of the markdown element is replaced every time we have new output
        log_pane.push(output)
    logging.info("command completed.")
    return total_output.find("FAILED") < 0

BRANCH_LIST=list_branches()