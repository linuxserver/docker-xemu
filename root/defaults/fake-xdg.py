#!/usr/bin/env python3
import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
import subprocess
import threading
import os

dbus.mainloop.glib.threads_init()
DBusGMainLoop(set_as_default=True)

class PortalRequest(dbus.service.Object):
    @dbus.service.signal('org.freedesktop.portal.Request', signature='ua{sv}')
    def Response(self, response, results):
        pass

class MicroPortal(dbus.service.Object):
    def __init__(self, bus):
        super().__init__(bus, '/org/freedesktop/portal/desktop')
        self.counter = 0

    @dbus.service.method(
        'org.freedesktop.portal.FileChooser',
        in_signature='ssa{sv}',
        out_signature='o'
    )
    def OpenFile(self, parent_window, title, options):
        return self._handle(title, options, False)

    @dbus.service.method(
        'org.freedesktop.portal.FileChooser',
        in_signature='ssa{sv}',
        out_signature='o'
    )
    def SaveFile(self, parent_window, title, options):
        return self._handle(title, options, True)

    def _handle(self, title, options, is_save):
        self.counter += 1
        req_path = f"/org/freedesktop/portal/desktop/request/1/req{self.counter}"
        req = PortalRequest(self.connection, req_path)

        def dialog_thread():
            home = os.path.expanduser('~') + '/'
            cmd = [
                'zenity', 
                '--file-selection', 
                f'--title={title}',
                f'--filename={home}'
            ]
            if is_save:
                cmd.append('--save')
            if options.get('directory'):
                cmd.append('--directory')
            
            try:
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode == 0:
                    path = res.stdout.strip()
                    results = dbus.Dictionary({
                        'uris': dbus.Array([f'file://{path}'], signature='s')
                    }, signature='sv')
                    GLib.idle_add(self._emit_response, req, 0, results)
                else:
                    empty_dict = dbus.Dictionary(signature='sv')
                    GLib.idle_add(self._emit_response, req, 1, empty_dict)
            except Exception:
                empty_dict = dbus.Dictionary(signature='sv')
                GLib.idle_add(self._emit_response, req, 2, empty_dict)

        threading.Thread(target=dialog_thread, daemon=True).start()
        return req_path

    def _emit_response(self, req, code, results):
        req.Response(dbus.UInt32(code), results)
        return False

if __name__ == "__main__":
    bus = dbus.SessionBus()
    name = dbus.service.BusName('org.freedesktop.portal.Desktop', bus)
    portal = MicroPortal(bus)
    GLib.MainLoop().run()
