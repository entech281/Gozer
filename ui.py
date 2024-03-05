import platform
from nicegui import ui, run, app
from datetime import datetime
import git_commands
import logging
import sys

class AppKeys:
    BUILD_HIST="builds"

ui.colors(primary='#367049')

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
        with BuildCard(gozer_build["id"]).classes('w-[600px] bg-gray-100 no-shadow border-[2px]') as card:
            with ui.row().classes():
                if gozer_build["success"] == True:
                    icon = 'check_circle'
                    label_color = 'text-green-700'
                    button_label = 'Rebuild'
                    icon_color = 'green-700'
                else:
                    icon = 'highlight_off'
                    button_label = 'Retry'
                    icon_color = 'red-700'
                    label_color = 'text-red-700'
                with ui.column().classes('w-12') :
                    ui.icon(icon,color=icon_color).classes('text-5xl')
                with ui.column():
                    msg = 'from {branch} on {date}'.format(branch=gozer_build["branch"], date=gozer_build["date_built"])
                    ui.label(gozer_build["id"]).classes(label_color + ' text-gray-500').style('font-size: 200%; font-weight: bold')
                    ui.label(msg).classes('text-gray-600').style('font-size: 120%; font-weight: bold')
                with ui.column().classes('w-64 no-wrap'):
                   with ui.row().classes():
                        ui.button(button_label, on_click=lambda id=gozer_build["id"]: build_ref(card.build_id),icon='refresh')
                        ui.button("Delete ", on_click=lambda c=card: c.delete_card() ,color='red',icon="dangerous")


async def build_ref(ref_to_build: str) -> None:
    log_pane.clear()
    git_hash = git_commands.run_checkout(ref_to_build)
    if git_hash is not None:

        success = await git_commands.run_deploy()
        add_build({
            "id": git_hash,
            "branch": ref_to_build,
            "date_built": nice_date(datetime.now()),
            "success": success
        })
        log_pane.push("DONE")


with ui.row().classes('w-full'):
    ui.image('gozer_image.png').classes('w-32')
    ui.label('Gozer the Deployer! v1.0').classes('text-green-800').style('font-size: 400%; font-weight: 200 color: #367049')
    ui.separator()
with ui.row().classes('w-full no-wrap'):
    with ui.column().classes('w-1/3'):
       with ui.card().classes('w-60  bg-gray-100'):
            ui.button('Deploy Main', on_click=lambda: build_ref('main'),icon="download")
       with ui.card().classes('w-60  bg-gray-100'):
            ui.button('Deploy Custom Ref', on_click=lambda: build_ref(user_ref.value),icon="download")
            user_ref = ui.input('Enter Ref').props('clearable')
       with ui.card().classes('w-60  bg-gray-100'):
            ui.button('Deploy Branch', on_click=lambda: build_ref(user_selected_ref.value),icon="download")
            user_selected_ref = ui.select(git_commands.BRANCH_LIST,value="main")
    with ui.column().classes('w-2/3 '):
        build_history()

with ui.card().classes('w-full'):
    ui.label('Logs').classes('w-full').classes('text-green-800').style(' font-weight: bold')
    log_pane = ui.log(max_lines=500).classes('w-full h-40').style('font-size: 80%')
    git_commands.set_log_pane(log_pane)
    ui.button('Clear Log', on_click=lambda: log_pane.clear(),icon="clear")

root = logging.getLogger()
root.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)
ui.run(host="127.0.0.1", port=8081,show=False,reload=platform.system() != 'Windows')
