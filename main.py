from nicegui import ui,run
from dulwich.repo import Repo
from dulwich import porcelain
import subprocess

REPO_PATH='/home/photonvision/gitwork/Robot2024/'

repo = Repo(REPO_PATH)
result_text=""

def list_branches():
    r =  porcelain.branch_list(repo)
    print(r)
    return r
    
@ui.refreshable
def build_output_ui():
     global result_text
     print("update ui, now result_text=",result_text)
     with ui.row():
        ui.html("Results:<pre>\n" + str(result_text) + "</pre>")
    
    
def run_build(gradle_command):
    global result_text
    cmd =  [ 'ls' , '-l']
    #cmd = ["gradlew",gradle_command ]
    result_text = subprocess.check_output(cmd, cwd=REPO_PATH, shell=True).decode()
    print ("Done, result=")
    print ( result_text)
    build_output_ui.refresh()

async def handle_run_build():
    result= await run.cpu_bound(run_build,"build")
    #build_output_ui.refresh()


async def handle_run_deploy():
    result= await run.cpu_bound(run_build,"deploy")
    #build_output_ui.refresh()

        
ui.html("<h1>Gozer the Deployer</h1>")

#with ui.row():
ui.button('Deploy Main To Robot', on_click=handle_run_deploy)
ui.button('Build Main', on_click=handle_run_build)
#ui.separator()
build_output_ui()
ui.run()
