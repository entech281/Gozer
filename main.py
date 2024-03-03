from nicegui import ui,run,app
import git_commands
from datetime import datetime

class AppKeys:
    BUILD_HIST="builds"

ui.colors(primary='#367049')

BRANCH_LIST=git_commands.list_branches()

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

    def delete_card(self) -> None:
        remove_build(self.build_id)
        self.delete()

def nice_date(dt):
    return dt.strftime("%m/%y %H:%M:%S")

@ui.refreshable
def build_history() -> None:
    for gozer_build in get_saved_builds():
        with BuildCard(gozer_build["id"]).classes('w-[600px] bg-gray-100') as card:
            with ui.row().classes():
                with ui.column():
                    msg = 'from {branch} on {date}'.format(branch=gozer_build["branch"], date=gozer_build["date_built"])
                    ui.label(gozer_build["id"]).classes('w-64 text-green-900').style('font-size: 200%; font-weight: bold')
                    ui.label(msg).classes('w-64 text-gray-600').style('font-size: 120%; font-weight: bold')
                with ui.column().classes('flow-root'):
                    with ui.row().classes('w-64 float-right'):
                        ui.button("Rebuild", on_click=lambda id=gozer_build["id"]: build_ref(card.build_id))
                        ui.button("Delete ", on_click=lambda c=card: c.delete_card() ,color="red")


async def build_ref(ref_to_build: str) -> None:
    log_pane.clear()
    git_hash = git_commands.run_checkout(ref_to_build)
    if git_hash is not None:
        log_pane.push("Running Gradle Build...")
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
            user_selected_ref = ui.select(git_commands.list_branches(),value="main")
    with ui.column().classes('w-2/3  bg-gray-100'):
        build_history()

with ui.card().classes('w-full'):

    ui.label('Logs').classes('w-full').style('font-color:black font-size: 80%; font-weight: bold')
    log_pane = ui.log(max_lines=500).classes('w-full h-40').style('font-sise: 80%')
    git_commands.set_log_pane(log_pane)
    ui.button('Clear Log', on_click=lambda: log_pane.clear())

#ui.run(host="127.0.0.1", port=8081,reload=platform.system() != 'Windows')
ui.run(host="127.0.0.1", port=8081,reload=True)
