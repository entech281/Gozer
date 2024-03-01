from nicegui import ui,run,app
from dulwich.repo import Repo
from dulwich import porcelain
import asyncio
from datetime import datetime
import subprocess

import os.path
import subprocess
import platform
import shlex
import sys
class AppKeys:
    BUILD_HIST="builds"

REPO_PATH='c:/users/davec/gitwork/Robot2024/'

def list_branches() -> list:
    branch_list_result=subprocess.run(['git','branch', '-l','--format',' %(refname)' ], cwd=REPO_PATH, capture_output=True,shell=True,check=False)
    if branch_list_result.returncode == 0:
        bl = branch_list_result.stdout.decode().split()
        #TODO: get git to return the regular branch name instead of this hack
        bl_without_stuff = []
        for b in bl:
            v = b.replace('refs/heads/','')
            bl_without_stuff.append(v)
        print("returning Branch List,", bl_without_stuff,type(bl_without_stuff))
        return bl_without_stuff
    else:
        print("Error Fetching Branches", branch_list_result.stderr)
        return []

BRANCH_LIST=list_branches()


if AppKeys.BUILD_HIST not in app.storage.general:
    app.storage.general[AppKeys.BUILD_HIST] = {}

def get_saved_builds():
    return list(app.storage.general[AppKeys.BUILD_HIST].values())

def add_build(build:dict):
    app.storage.general[AppKeys.BUILD_HIST][build['id']]=build
    build_history.refresh()

def remove_build(build_id:str):
    d = app.storage.general[AppKeys.BUILD_HIST]
    del d[build_id]
    build_history.refresh()

repo = Repo(REPO_PATH)
log_pane=None

def nice_date(dt):
    return dt.strftime("%m/%y %H:%M ")

@ui.refreshable
def build_history() -> None:
    with ui.list().props('separator'):
        for gozer_build in get_saved_builds():
            with ui.item() as item:
                with ui.item_section():
                    ui.item_label(gozer_build["id"]).style('font-size: 200%; font-weight: 300')
                    with ui.row():
                        ui.label("(from {ref} at {d}".format(ref=gozer_build["branch"],d=gozer_build["date_built"])).style('font-size: 100%;')
                        ui.button("Rebuild", on_click=lambda: build_ref(gozer_build["id"]))
                        def delete_me():
                            item.delete()
                            remove_build(gozer_build["id"])
                        ui.button("Delete ", on_click=delete_me)

def run_checkout(ref: str) -> str:
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

async def build_ref(ref_to_build: str) -> None:
    log_pane.clear()
    git_hash = run_checkout(ref_to_build)
    if git_hash is not None:
        log_pane.push("Running Gradle Build...")
        await run_command('.\gradlew build')
        add_build({
            "id": git_hash,
            "branch": ref_to_build,
            "date_built": nice_date(datetime.now())
        })


with ui.row():
    ui.label('Gozer the Deployer!').style('color: #367049; font-size: 400%; font-weight: 300')
with ui.row():
    with ui.column():
       with ui.card():
            ui.button('Build Main', on_click=lambda: build_ref('main'))
       with ui.card():
            ui.button('Build Custom Ref', on_click=lambda: build_ref(user_ref.value))
            user_ref = ui.input('Enter Ref').props('clearable')
       with ui.card():
            user_selected_ref = ui.select(list_branches())
            ui.button('Build Branch', on_click=lambda: build_ref(user_selected_ref.value))
    with ui.column():
        build_history()

with ui.card().classes('w-full'):
    ui.label('Logs').style('color: #367049; font-size: 100%; font-weight: 300')
    log_pane = ui.log(max_lines=500).classes('w-full h-80')
    ui.button('Clear Log', on_click=lambda: log_pane.clear())

ui.run(host="127.0.0.1", port=8081,reload=platform.system() != 'Windows')
