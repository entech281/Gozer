import platform
from nicegui import ui, run, app
from datetime import datetime
import asyncio
import networkscan
import git_commands
import logging
import sys

class AppKeys:
    BUILD_HIST="builds"
    TEAM_NUMBER="team_number"
    TARGET_NETWORK="target_network"

ui.colors(primary='#367049')

if AppKeys.BUILD_HIST not in app.storage.general:
    app.storage.general[AppKeys.BUILD_HIST] = {}

if AppKeys.TEAM_NUMBER not in app.storage.general:
    app.storage.general[AppKeys.TEAM_NUMBER] = 281

if AppKeys.TARGET_NETWORK not in app.storage.general or len(str(app.storage.general.get(AppKeys.TARGET_NETWORK, ""))) < 5:
    team = app.storage.general.get(AppKeys.TEAM_NUMBER, 281)
    try: team = int(team)
    except ValueError: team = 281
    app.storage.general[AppKeys.TARGET_NETWORK] = f"10.{team // 100}.{team % 100}.0/24"

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

    result = await git_commands.run_deploy(ref_to_build)
    if result.success:
        add_build({
            "id": result.hash,
            "branch": ref_to_build,
            "date_built": nice_date(datetime.now()),
            "success": True
        })
        log_pane.push("Deploy {ref} [SUCCESS]".format(ref=ref_to_build))
    else:
        ui.notify("Problem! {p}".format(p=result.message), type='negative', close_button="CLOSE" )
        log_pane.push("Deploy {ref} [FAILED]".format(ref=ref_to_build))


with ui.right_drawer(value=True).classes('bg-gray-100 border-l') as right_drawer:
    with ui.row().classes('w-full items-center justify-between'):
        ui.label('Network Scanner').classes('text-lg font-bold text-green-800')
    
    def update_team_number(e):
        app.storage.general[AppKeys.TEAM_NUMBER] = e.value
        try:
            team = int(e.value)
            new_net = f"10.{team // 100}.{team % 100}.0/24"
            app.storage.general[AppKeys.TARGET_NETWORK] = new_net
            network_input.value = new_net
        except ValueError:
            pass

    def update_network(e):
        app.storage.general[AppKeys.TARGET_NETWORK] = e.value

    ui.input('FRC Team Number', value=str(app.storage.general.get(AppKeys.TEAM_NUMBER, 281)), on_change=update_team_number).classes('w-full')
    network_input = ui.input('Target Network', value=app.storage.general.get(AppKeys.TARGET_NETWORK, "10.2.81.0/24"), on_change=update_network).classes('w-full mb-2')
    
    scan_button = ui.button('Scan Network', on_click=lambda: ui.timer(0.1, scan_network, once=True), icon='search').classes('w-full mt-2')
    scan_progress = ui.linear_progress(value=0.0, show_value=False).props('size="15px" rounded').classes('w-full mt-2')
    scan_progress_label = ui.label('0%').classes('text-xs text-center w-full font-bold text-gray-500 pt-1')
    scan_progress.set_visibility(False)
    scan_progress_label.set_visibility(False)

    ui.separator().classes('my-2')
    ui.label('Discovered Devices').classes('font-bold text-gray-700')
    device_list_container = ui.column().classes('w-full')

is_scanning = False

async def scan_network():
    global is_scanning
    if is_scanning:
        return
    is_scanning = True

    scan_button.disable()
    scan_progress.set_visibility(True)
    scan_progress_label.set_visibility(True)
    scan_progress.value = 0.0
    scan_progress_label.text = '0%'

    async def update_progress():
        progress = 0.0
        while is_scanning and progress < 0.90:
            await asyncio.sleep(0.15)
            if not is_scanning: break
            progress += 0.05
            scan_progress.value = progress
            scan_progress_label.text = f"{int(progress * 100)}%"

    progress_task = asyncio.create_task(update_progress())

    try:
        network = app.storage.general.get(AppKeys.TARGET_NETWORK, "10.2.81.0/24")
        
        def run_scan():
            import networkscan
            scan = networkscan.Networkscan(network)
            scan.run()
            return scan.list_of_hosts_found
            
        try:
            hosts = await run.io_bound(run_scan)
            
            scan_progress.value = 1.0
            scan_progress_label.text = '100%'
            
            device_list_container.clear()
            with device_list_container:
                if not hosts:
                    ui.label(f"No devices found on {network}").classes('text-gray-500 italic text-sm')
                else:
                    for h in hosts:
                        ui.label(h).classes('text-sm')
        except Exception as e:
            device_list_container.clear()
            with device_list_container:
                ui.label(f"Scan failed: {str(e)}").classes('text-red-500 text-sm')
    finally:
        is_scanning = False
        scan_button.enable()
        await asyncio.sleep(0.5)
        scan_progress.set_visibility(False)
        scan_progress_label.set_visibility(False)

with ui.row().classes('w-full items-center justify-between'):
    with ui.row().classes('items-center'):
        ui.image('gozer_image.png').classes('w-32')
        ui.label('Gozer the Deployer! v1.0').classes('text-green-800').style('font-size: 400%; font-weight: 200 color: #367049')
    ui.button('Scanner', icon='menu', on_click=right_drawer.toggle).classes('bg-green-700 text-white')

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
    log_pane = ui.log(max_lines=1000).classes('w-full h-40').style('font-size: 80%')
    git_commands.set_log_pane(log_pane)
    ui.button('Clear Log', on_click=lambda: log_pane.clear(),icon="clear")

# Scanner logic moved to the top of layout
root = logging.getLogger()
root.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)
ui.run(host="0.0.0.0", port=8081,show=False,reload=platform.system() != 'Windows')
