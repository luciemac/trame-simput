from pathlib import Path
from trame.app import get_server
from trame.ui.vuetify import SinglePageWithDrawerLayout
from trame.widgets import vuetify, simput

from trame_simput import get_simput_manager
from trame_simput.core.proxy import Proxy
from trame_server.state import State

# -----------------------------------------------------------------------------
# Trame setup
# -----------------------------------------------------------------------------

server = get_server()
state, ctrl = server.state, server.controller

state.companies_ids = {} # Needed to be reactive

# -----------------------------------------------------------------------------
# Simput initialization
# -----------------------------------------------------------------------------

DEF_DIR = Path(__file__).with_name("definitions")

simput_manager = get_simput_manager()
simput_manager.load_model(yaml_file=DEF_DIR / "model.yaml")
simput_manager.load_ui(xml_file=DEF_DIR / "model.xml")

class PersonModel:
    MODEL_TYPE = "Person"

    def __init__(self, server, pxm):
        self._state: State = server.state
        self._pxm = pxm

        # state
        self.update_state()

        # ctrl
        ctrl = server.controller
        ctrl.create_person = self.create_entry
        ctrl.delete_active_person = self.delete_active
        ctrl.add_company = self.create_company
        ctrl.remove_company = self.remove_company
        
    def create_entry(self):
        obj = self._pxm.create(PersonModel.MODEL_TYPE)
        self.update_state(obj.id)

    def delete_active(self):
        if self._state.active_id is not None:
            self._pxm.delete(self._state.active_id)
            self.update_state()

    def update_state(self, active_id=None):
        self._state.active_id = active_id
        self._state.person_ids = [p.id for p in self._pxm.get_instances_of_type(PersonModel.MODEL_TYPE)]

    def create_company(self, parent_proxy_id: str) -> None:
        parent_proxy: Proxy = self._pxm.get(parent_proxy_id)
        if not parent_proxy:
            return
        
        subproxy_type = parent_proxy.definition.get("Companies").get("_subproxy_type")
        if not subproxy_type:
            return
        
        subproxy: Proxy = self._pxm.create(subproxy_type)
        parent_proxy["Companies"] = parent_proxy["Companies"] + [subproxy.id]
        parent_proxy.commit()
        self.update_state_companies_ids(parent_proxy_id)

    def remove_company(self, parent_proxy_id: str, company_id_to_remove: str) -> None:
        parent_proxy: Proxy = self._pxm.get(parent_proxy_id)
        if not parent_proxy:
            return
        
        companies_ids = parent_proxy.get_property('Companies')
        self._pxm.delete(company_id_to_remove)
        parent_proxy["Companies"] = [i for i in companies_ids if i != company_id_to_remove]
        parent_proxy.commit()
        self.update_state_companies_ids(parent_proxy_id)

    
    def update_state_companies_ids(self, parent_proxy_id: str) -> None:
        parent_proxy: Proxy = self._pxm.get(parent_proxy_id)
        if not parent_proxy:
            return
        self._state.companies_ids[parent_proxy_id] = [company_id for company_id in parent_proxy["Companies"]]
        self._state.dirty("companies_ids")

# -----------------------------------------------------------------------------
# Graphical Interface
# -----------------------------------------------------------------------------

btn_styles = {
    "classes": "mx-2",
    "small": True,
    "outlined": True,
    "icon": True,
}

compact_styles = {
    "hide_details": True,
    "dense": True,
}

# -----------------------------------------------------------------------------
# Simput container initialization
# -----------------------------------------------------------------------------

simput_widget = simput.Simput(simput_manager, trame_server=server)
ctrl.simput_apply = simput_widget.apply
ctrl.simput_reset = simput_widget.reset

# -----------------------------------------------------------------------------
# Layout
# -----------------------------------------------------------------------------
def companies_layout():
    with vuetify.VExpansionPanels(
        v_if="active_id",
        flat=True,
        accordion=True,
        v_for="(property_name, i) in ['Companies']",
        key="i",
        value=("property_name",),
    ), vuetify.VExpansionPanel():
        with vuetify.VExpansionPanelHeader("{{ property_name }}", classes="pl-3"), vuetify.Template(
            v_slot_actions="{open}",
        ):            
            with vuetify.VBtn(
                **btn_styles,
                click=(
                    ctrl.add_company,
                    "[active_id]",
                    "$event.stopPropagation()",
                ),
            ):
                vuetify.VIcon("mdi-plus")

        vuetify.VDivider()
        with vuetify.VExpansionPanelContent(), vuetify.VList(hide_details=True, dense=True):
            with (
                vuetify.VListItem(
                    v_for="(company_id, i) in companies_ids[active_id]",
                    key="i",
                    value=("company_id",),
                ),
                vuetify.VListItemContent(),
                vuetify.VListItemTitle(),
                vuetify.VContainer(),
                vuetify.VRow()
            ):
                with vuetify.VCol():
                    simput.SimputItem(item_id="company_id")
                with vuetify.VCol(cols=2):
                    with vuetify.VBtn(
                        **btn_styles,
                        click=(
                            ctrl.remove_company,
                            "[active_id, company_id]",
                        ),
                    ):
                        vuetify.VIcon("mdi-minus")


with SinglePageWithDrawerLayout(server) as layout:
    layout.title.set_text("SimPut - List of proxies")
    simput_widget.register_layout(layout)

    with layout.toolbar:
        vuetify.VSpacer()
        with vuetify.VBtn(
            **btn_styles,
            disabled=("!active_id",),
            click=ctrl.delete_active_person,
        ):
            vuetify.VIcon("mdi-minus")

        with vuetify.VBtn(click=ctrl.create_person, **btn_styles):
            vuetify.VIcon("mdi-plus")

    with (
        layout.drawer, 
        vuetify.VList(**compact_styles), 
        vuetify.VListItemGroup(v_model="active_id", color="primary"),
        vuetify.VListItem(
            v_for="(id, i) in person_ids",
            key="i",
            value=("id",),
        ),
        vuetify.VListItemContent(), vuetify.VListItemTitle()
    ):
        simput.SimputItem(
            "{{FirstName}} {{LastName}}",
            item_id="id",
            no_ui=True,
            extract=["FirstName", "LastName"],
        )

    with layout.content, vuetify.VContainer(fluid=True):
        simput.SimputItem(item_id=("active_id", None))
        companies_layout()

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    engine = PersonModel(server, simput_manager.proxymanager)
    server.start()
