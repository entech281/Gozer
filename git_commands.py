import subprocess
import asyncio
import configparser
import os.path
import logging
from dataclasses import dataclass

log_pane = None
REPO_PATH=None
BRANCH_LIST=[]
DEBUG_ON=False
ROBORIO_IP="10.2.81.16"
GITEA_IP="10.2.81.10"

CONFIG_FILE= "gozer.ini"

config=configparser.ConfigParser()
config.read(CONFIG_FILE)
path_to_try=config['DEFAULT']['repo_path']

if not path_to_try:
    raise ValueError("Can't find gozer.ini. expecting it alongside the source in the git project")

if not os.path.exists(path_to_try):
    raise ValueError("Repo Path '{s}' Does not appear to be valid in gozer.ini".format(s=path_to_try))

REPO_PATH = path_to_try
DEPLOY_ENABLED = (config['DEFAULT']['enable_deploy'].lower() in ['true', '1', 't', 'y', 'yes'])


@dataclass
class RunResult:
    success: bool
    message: str
    hash: str

logging.info("Repository Path: ", REPO_PATH)
logging.info("Deploys Enabled:", DEPLOY_ENABLED)

def set_log_pane(d):
   global log_pane
   log_pane = d

def info_message(message):
    log_pane.push(message)
    logging.info(message)

def debug_message(message):
    if DEBUG_ON:
        log_pane.push('[DEBUG] ' + message)
    logging.debug(message)

def update_branches():
    global BRANCH_LIST
    BRANCH_LIST = list_branches()

def list_branches() -> list:
    branch_list_result=subprocess.run("git branch -l --format '%(refname)'", cwd=REPO_PATH, capture_output=True,shell=True,check=False)
    if branch_list_result.returncode == 0:
        bl = branch_list_result.stdout.decode().split()
        bl_without_stuff = []
        for b in bl:
            v = b.replace('refs/heads/','')
            bl_without_stuff.append(v)
        return bl_without_stuff
    else:
        return []

async def run_deploy(ref:str) -> RunResult:
    def gradle_command(command)-> str:
        return  os.path.join(".", "gradlew --offline ") + command

    def ping_command(ip_addr:str) -> str:
        return "ping -c 2 -W 1 " + ip_addr

    r = _short_command("Check For Roborio ", ping_command(ROBORIO_IP) )
    if r.returncode != 0:
        return RunResult(success=False,message="Could not find RoboRio. Are we plugged into the robot?",hash="<none>")

    r = _short_command("Check For Gitea ", ping_command(GITEA_IP) )
    if r.returncode != 0:
        return RunResult(success=False,message="Could not find Gitea. Is the programmer field kit connected?",hash="<none>")

    r = _short_command("Fetch Remote", 'git fetch --all')
    if r.returncode != 0:
        return RunResult(success=False,message="Couldnt Pull from Gitea. Is the repo cloned right?",hash="<none>" )

    update_branches()

    r = _short_command("Checking out ref {ref}".format(ref=ref), 'git checkout -f {ref}'.format(ref=ref))
    if r.returncode != 0:
        return RunResult(success=False,message="Couldnt check out that ref. Is it valid??" ,hash="<none>")

    r = _short_command(("Getting ref for this branch"),'git rev-parse --short HEAD')
    if r.returncode != 0:
        return RunResult(success=False,message="Inexplicably, couldnt compute hash for this ref?" ,hash="<none>")
    else:
        git_hash = r.stdout.decode()
        debug_message("'{ref}'=={git_hash}".format(ref=ref, git_hash=git_hash))

    info_message("Running Gradle Build...")
    successful_build = await _run_long_command(gradle_command('build'))

    if not successful_build:
        return RunResult(success=False,message="Gradle Build failed. Need a programmer!",hash=git_hash)

    if DEPLOY_ENABLED:
        info_message("Running Gradle Deploy...")
        successful_deploy = await _run_long_command(gradle_command('deploy'))
        if successful_deploy:
            return RunResult(success=True,message="Successfully deployed ref {ref}".format(ref=ref),hash=git_hash)
        else:
            return RunResult(success=False, message="Error deploying ref {ref}".format(ref=ref),hash=git_hash)
    else:
        info_message("Not Deploying: Deploys are disabled")
        return RunResult(success=True,message="Built, but did not deploy ref {ref}".format(ref=ref),hash=git_hash)


def _short_command(friendly_name: str, command: str) -> subprocess.CompletedProcess:
    "Runs a command and returns is output in a single shot. used for quick commands"

    debug_message("Running command: '{c}'".format(c=command))
    r = subprocess.run(command, cwd=REPO_PATH, capture_output=True, shell=True, check=False)

    if r.returncode == 0:
        info_message(friendly_name + "[ OK ]")

    else:
        info_message(friendly_name + "[ FAILED ]")
        info_message("ERROR: {s}".format(s=str(r)))

    return r


async def _run_long_command(command: str) -> bool:

    debug_message("running command {s}".format(s=command))
    process = await asyncio.create_subprocess_shell(command,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,shell=True,cwd=REPO_PATH
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
        info_message(output)

    debug_message("command completed. return code={d}".format(d=process.returncode))
    return process.returncode == 0 and total_output.find("FAILED") < 0


update_branches()