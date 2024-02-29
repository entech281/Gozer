from nicegui import ui,run
from dulwich.repo import Repo
from dulwich import porcelain
import asyncio
import os.path
import subprocess
import platform
import shlex
import sys
REPO_PATH='c:/users/davec/gitwork/Robot2024/'

repo = Repo(REPO_PATH)

log_pane=None

def list_branches():
    r = porcelain.branch_list(repo)
    print(r)
    return r

async def run_command(command: str) -> None:
    """Run a command in the background and display the output in the pre-created dialog."""
    process = await asyncio.create_subprocess_shell(command,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
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


ui.label('Gozer the Deployer!').style('color: #367049; font-size: 100%; font-weight: 300')
with ui.row():
   ui.button('Build Main', on_click=lambda: run_command('.\gradlew build'))
ui.separator()
log_pane = ui.log(max_lines=500).classes('w-full h-80')
ui.button('Clear Log', on_click=lambda: log_pane.clear() )
ui.run(host="127.0.0.1", port=8081,reload=platform.system() != 'Windows')
