

__kupfer_name__ = _("Gwibber (Simple)")
__kupfer_actions__ = (
        "SendUpdate",
    )
__description__ = _("Send updates via the microblogging client Gwibber")
__version__ = ""
__author__ = ""

import dbus

from kupfer.objects import Action, TextLeaf, OperationError
from kupfer import plugin_support
from kupfer import pretty

plugin_support.check_dbus_connection()

SERVICE_NAME = "com.Gwibber.Service"
OBJ_NAME = "/com/gwibber/Service"
IFACE_NAME = "com.Gwibber.Service"


def _get_interface(activate=False):
    """Return the dbus proxy object for our Note Application.

    if @activate, we will activate it over d-bus (start if not running)
    """
    bus = dbus.SessionBus()
    proxy_obj = bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
    dbus_iface = dbus.Interface(proxy_obj, 'org.freedesktop.DBus')

    if not activate and not dbus_iface.NameHasOwner(SERVICE_NAME):
        return

    try:
        proxyobj = bus.get_object(SERVICE_NAME, OBJ_NAME)
    except dbus.DBusException as e:
        pretty.print_error(__name__, e)
        return
    return dbus.Interface(proxyobj, IFACE_NAME)

class SendUpdate (Action):
    def __init__(self):
        Action.__init__(self, _("Send Update"))

    def wants_context(self):
        return True

    def activate(self, leaf, ctx):
        def success_cb():
            pretty.print_debug(__name__, "Successful D-Bus method call")

        def err_cb(exc):
            exc_info = (type(exc), exc, None)
            ctx.register_late_error(exc_info)

        gwibber = _get_interface(True)
        if gwibber:
            gwibber.SendMessage(leaf.object,
                                reply_handler=success_cb, error_handler=err_cb)
        else:
            pretty.print_error(__name__, "Gwibber Service not found as:",
                               (SERVICE_NAME, OBJ_NAME, IFACE_NAME))
            raise OperationError(_("Unable to activate Gwibber service"))

    def item_types(self):
        yield TextLeaf

    def get_description(self):
        return __description__

