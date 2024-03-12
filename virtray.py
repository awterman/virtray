import os
import subprocess
import sys
import time
from typing import Callable

import libvirt
import toml
from pydantic import BaseModel
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import QApplication, QMenu, QSystemTrayIcon


class Item(BaseModel):
    icon: str
    domain: str


class Config(BaseModel):
    items: list[Item]


class WmctrlItem(BaseModel):
    window_id: str
    title: str


def load_config(path: str) -> Config:
    d = toml.load(path)
    return Config.model_validate(d)


def execute_command(command: str) -> str:
    p = subprocess.run(command, shell=True, capture_output=True)
    ret = p.stdout.decode("utf-8")
    return ret


class WindowManager:
    @staticmethod
    def get_wmctrl_items() -> list[WmctrlItem]:
        p = execute_command("wmctrl -l").strip()
        items = []
        for line in p.split("\n"):
            window_id, _, _, title = line.split(sep=None, maxsplit=3)
            items.append(WmctrlItem(window_id=window_id, title=title))
        return items

    @staticmethod
    def try_get_wmctrl_item(
        is_target_title: Callable[[str], bool]
    ) -> tuple[WmctrlItem, bool]:
        items = WindowManager.get_wmctrl_items()
        for item in items:
            if is_target_title(item.title):
                return item, True
        return None, False

    @staticmethod
    def open_virt_manager(domain: str) -> None:
        execute_command(
            f"virt-manager --connect=qemu:///system --show-domain-console={domain}"
        )

        # set focus to the window
        for _ in range(10):
            item, found = WindowManager.try_get_wmctrl_item(
                WindowManager.virt_manager_target_title(domain)
            )
            if found:
                execute_command(f"wmctrl -ia {item.window_id}")
                break
            time.sleep(0.1)

    @staticmethod
    def is_window_open(is_target_title: Callable[[str], bool]) -> bool:
        p = execute_command("wmctrl -l").strip()
        for line in p.split("\n"):
            if is_target_title(line.split(sep=None, maxsplit=3)[-1]):
                return True
        return False

    @staticmethod
    def close_window(is_target_title: Callable[[str], bool]):
        for item in WindowManager.get_wmctrl_items():
            if is_target_title(item.title):
                execute_command(f"wmctrl -ic {item.window_id}")

    @staticmethod
    def virt_manager_target_title(domain: str) -> Callable[[str], bool]:
        target = f"{domain} on QEMU/KVM"

        def is_target_title(title: str) -> bool:
            return title == target

        return is_target_title

    @staticmethod
    def trigger_virt_manager(domain: str) -> None:
        if WindowManager.is_window_open(
            WindowManager.virt_manager_target_title(domain)
        ):
            WindowManager.close_window(WindowManager.virt_manager_target_title(domain))
        else:
            WindowManager.open_virt_manager(domain)


class LibvirtManager:
    def __init__(self, show_message: Callable[[str], None] = print) -> None:
        self.conn = libvirt.open("qemu:///system")
        self.show_message = show_message

    def get_save_path(self, domain: str) -> str:
        return f"/var/lib/libvirt/qemu/save/{domain}.save"

    def save(self, domain: str) -> None:
        self.show_message(f"saving {domain}")
        dom = self.conn.lookupByName(domain)
        dom.save(self.get_save_path(domain))
        self.show_message(f"saved to {self.get_save_path(domain)}")

    def restore(self, domain: str) -> None:
        self.show_message(f"restoring {domain}")
        self.conn.restore(self.get_save_path(domain))
        self.show_message(f"restored from {self.get_save_path(domain)}")

    def is_saved(self, domain: str) -> bool:
        return os.path.exists(self.get_save_path(domain))

    def is_running(self, domain: str) -> bool:
        dom = self.conn.lookupByName(domain)
        return dom.isActive() == 1

    def start(self, domain: str) -> None:
        self.show_message(f"starting {domain}")
        dom = self.conn.lookupByName(domain)
        dom.create()
        self.show_message(f"started {domain}")

    def force_shutdown(self, domain: str) -> None:
        self.show_message(f"force shutting down {domain}")
        dom = self.conn.lookupByName(domain)
        dom.destroy()
        self.show_message(f"force shut down {domain}")


class VirtTray:
    def __init__(self, virt: LibvirtManager, config: Config) -> None:
        self.app = QApplication(sys.argv)
        self.virt = virt
        self.config = config

    def save_all(self) -> None:
        for item in self.config.items:
            if self.virt.is_running(item.domain):
                self.virt.save(item.domain)

    def restore_all(self) -> None:
        for item in self.config.items:
            if self.virt.is_saved(item.domain):
                self.virt.restore(item.domain)

    def create_tray_icon(self, item: Item) -> None:
        icon = QIcon(item.icon)
        trayIcon = QSystemTrayIcon(icon, self.app)
        trayIcon.setToolTip(item.domain)

        menu = QMenu()
        virt = LibvirtManager(
            show_message=lambda msg: trayIcon.showMessage(
                "Virtray", msg, icon=QSystemTrayIcon.NoIcon, msecs=3000
            )
        )

        startAction = menu.addAction("Start")
        # set to enabled if not running
        startAction.setEnabled(not virt.is_running(item.domain))
        startAction.triggered.connect(lambda: virt.start(item.domain))

        forceShutdownAction = menu.addAction("Force Shutdown")
        # set to enabled if running
        forceShutdownAction.setEnabled(virt.is_running(item.domain))
        forceShutdownAction.triggered.connect(lambda: virt.force_shutdown(item.domain))

        saveAction = menu.addAction("Save")
        # set to enabled if running and not saved
        saveAction.setEnabled(
            virt.is_running(item.domain) and not virt.is_saved(item.domain)
        )
        saveAction.triggered.connect(lambda: virt.save(item.domain))

        restoreAction = menu.addAction("Restore")
        # set to enabled if saved
        restoreAction.setEnabled(virt.is_saved(item.domain))
        restoreAction.triggered.connect(lambda: virt.restore(item.domain))

        # separator
        menu.addSeparator()

        saveAllAction = menu.addAction("Save All")
        saveAllAction.triggered.connect(self.save_all)

        restoreAllAction = menu.addAction("Restore All")
        restoreAllAction.triggered.connect(self.restore_all)

        quitAction = menu.addAction("Quit")
        quitAction.triggered.connect(self.app.quit)

        trayIcon.activated.connect(
            lambda reason, domain=item.domain: (
                WindowManager.trigger_virt_manager(domain)
                if reason == QSystemTrayIcon.Trigger
                else None
            )
        )

        def update_menu(
            startAction=startAction,
            forceShutdownAction=forceShutdownAction,
            saveAction=saveAction,
            restoreAction=restoreAction,
            item=item,
        ):
            print("update_menu")
            startAction.setEnabled(not virt.is_running(item.domain))
            forceShutdownAction.setEnabled(virt.is_running(item.domain))
            saveAction.setEnabled(
                virt.is_running(item.domain) and not virt.is_saved(item.domain)
            )
            restoreAction.setEnabled(virt.is_saved(item.domain))

        menu.aboutToShow.connect(update_menu)

        trayIcon.setContextMenu(menu)

        trayIcon.show()

    def main(self):
        for item in self.config.items:
            self.create_tray_icon(item)

        sys.exit(self.app.exec_())


def main(config_path: str):
    virt = LibvirtManager()
    config = load_config(config_path)

    virt_tray = VirtTray(virt=virt, config=config)
    virt_tray.main()


if __name__ == "__main__":
    config_path = "config.toml"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]

    main(config_path)
