from pathlib import Path
from trame.app import get_server
from trame.ui.vuetify import SinglePageWithDrawerLayout
from trame.widgets import vuetify, simput

from trame_simput import get_simput_manager
from trame_simput.core.proxy import Proxy

# -----------------------------------------------------------------------------
# Trame setup
# -----------------------------------------------------------------------------

server = get_server()
state, ctrl = server.state, server.controller


# -----------------------------------------------------------------------------
# Simput initialization
# -----------------------------------------------------------------------------

DEF_DIR = Path(__file__).with_name("definitions")

simput_manager = get_simput_manager()
simput_manager.load_model(yaml_file=DEF_DIR / "model.yaml")
simput_manager.load_ui(xml_file=DEF_DIR / "model.xml")

class DynamicModel:
    MODEL_TYPE = "DynamicModel"

    def __init__(self, server, pxm):
        self._state = server.state
        self._pxm = pxm

        # state
        self.update_state()

        # ctrl
        ctrl = server.controller
        ctrl.add_object = self.create_entry
        ctrl.delete_active = self.delete_active

    def _update_type_parameters(self):
        proxy: Proxy = self._pxm.get(self.active_id)
        if proxy is None:
            return
        type = proxy['Type']
        model_type = "Parameter" if type == 'type1' else "Parameter2"
        # Check if there is already a Parameters proxy and remove it if necessary
        parameters_proxy = proxy["Parameters"]
        if parameters_proxy is not None:
            self._pxm.delete(parameters_proxy.id)
        proxy["Parameters"] = self._pxm.create(model_type)
        # proxy.commit()

    def on_change(self, topic, **kwargs):
        property_name = kwargs.get("property_name", None)
        if property_name is None:
            return
        if topic == "update" and property_name == 'Type':
            self._update_type_parameters()
        
    def create_entry(self):
        obj = self._pxm.create(DynamicModel.MODEL_TYPE)
        obj.on(self.on_change)
        self.update_state(obj.id)

    def delete_active(self):
        if self.active_id:
            self._pxm.delete(self.active_id)
            self.update_state()

    def update_state(self, active_id=None):
        self._state.active_id = active_id
        self._state.obj_ids = self.entry_ids

    @property
    def active_id(self):
        return self._state.active_id

    @property
    def entry_ids(self):
        return [p.id for p in self._pxm.get_instances_of_type(DynamicModel.MODEL_TYPE)]


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

with SinglePageWithDrawerLayout(server) as layout:
    layout.title.set_text("SimPut Dynamic Model Example")
    simput_widget.register_layout(layout)

    with layout.toolbar:
        vuetify.VSpacer()
        with vuetify.VBtn(
            **btn_styles,
            disabled=("!active_id",),
            click=ctrl.delete_active,
        ):
            vuetify.VIcon("mdi-minus")

        with vuetify.VBtn(click=ctrl.add_object, **btn_styles):
            vuetify.VIcon("mdi-plus")

    with layout.drawer:
        with vuetify.VList(**compact_styles):
            with vuetify.VListItemGroup(v_model="active_id", color="primary"):
                with vuetify.VListItem(
                    v_for="(id, i) in obj_ids",
                    key="i",
                    value=("id",),
                ):
                    with vuetify.VListItemContent():
                        with vuetify.VListItemTitle():
                            simput.SimputItem(
                                "{{Name}}",
                                item_id="id",
                                no_ui=True,
                                extract=["Name"],
                            )

    with layout.content:
        with vuetify.VContainer(fluid=True):
            simput.SimputItem(item_id=("active_id", None))


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    engine = DynamicModel(server, simput_manager.proxymanager)
    server.start()