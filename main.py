from nicegui import ui,run,app
import asyncio
from datetime import datetime
import subprocess
import platform

class AppKeys:
    BUILD_HIST="builds"

REPO_PATH='c:/users/davec/gitwork/Robot2023/'

ui.colors(primary='#367049')

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
    if build_id in d.keys():
        del d[build_id]
    build_history.refresh()

log_pane=None

class BuildCard(ui.card):

    def __init__(self, build_id,*args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.build_id = build_id
        #self.on('click', self.delete_card)

    def delete_card(self) -> None:
        print("Deleting Card, removing build: ",self.build_id)
        remove_build(self.build_id)
        self.delete()

def nice_date(dt):
    return dt.strftime("%m/%y %H:%M:%S")

@ui.refreshable
def build_history() -> None:

    for gozer_build in get_saved_builds():
        with BuildCard(gozer_build["id"]).classes('w-[600px] bg-gray-100') as card:
            with ui.row():
                with ui.column():
                    msg = 'from {branch} on {date}'.format(branch=gozer_build["branch"], date=gozer_build["date_built"])
                    ui.label(gozer_build["id"]).classes('w-64 text-green-900').style('font-size: 200%; font-weight: bold')
                    ui.label(msg).classes('w-64 text-gray-600').style('font-size: 120%; font-weight: bold')
                with ui.column().classes('flow-root'):
                    with ui.row().classes('w-64 float-right'):
                        ui.button("Rebuild", on_click=lambda id=gozer_build["id"]: build_ref(card.build_id))
                        ui.button("Delete ", on_click=lambda c=card: c.delete_card() ,color="red")


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

async def build_ref(ref_to_build: str) -> None:
    log_pane.clear()
    git_hash = run_checkout(ref_to_build)
    #git_hash='1234'
    if git_hash is not None:
        log_pane.push("Running Gradle Build...")
        #await run_command('.\gradlew build')
        add_build({
            "id": git_hash,
            "branch": ref_to_build,
            "date_built": nice_date(datetime.now())
        })
        log_pane.push("DONE")


with ui.row().classes('w-full'):
    ui.label('Gozer the Deployer!').style('font-size: 400%; font-weight: 300')
    ui.separator()
with ui.row().classes('w-full no-wrap'):
    with ui.column().classes('w-1/3'):
       with ui.card().classes('w-60  bg-gray-100'):
            ui.button('Build Main', on_click=lambda: build_ref('main'))
       with ui.card().classes('w-60  bg-gray-100'):
            ui.button('Build Custom Ref', on_click=lambda: build_ref(user_ref.value))
            user_ref = ui.input('Enter Ref').props('clearable')
       with ui.card().classes('w-60  bg-gray-100'):
            ui.button('Build Branch', on_click=lambda: build_ref(user_selected_ref.value))
            user_selected_ref = ui.select(list_branches(),value="main")
    with ui.column().classes('w-2/3  bg-gray-100'):
        build_history()

with ui.card().classes('w-full'):

    ui.label('Logs').classes('w-full').style('font-color:black font-size: 80%; font-weight: bold')
    log_pane = ui.log(max_lines=500).classes('w-full h-40').style('font-sise: 80%')
    ui.button('Clear Log', on_click=lambda: log_pane.clear())

#ui.run(host="127.0.0.1", port=8081,reload=platform.system() != 'Windows')
ui.run(host="127.0.0.1", port=8081,reload=True)
