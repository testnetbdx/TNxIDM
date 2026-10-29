"""TNxIDM GUI - PySide6, Liquid Glass approximation.

Note: true real-time light refraction like Apple's is not possible in Qt.
This is the closest frosted-glass approximation: RGBA fills, specular
1px top-edge highlights, large radii, soft drop shadows and layered gradients.
"""
import math, os, re, subprocess, sys, time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QDateTime
from PySide6.QtGui import QAction, QColor, QPainter, QLinearGradient, QBrush
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QTableWidget, QTableWidgetItem, QPushButton, QLineEdit, QLabel,
    QDialog, QFormLayout, QComboBox, QSpinBox, QCheckBox, QFileDialog, QMessageBox,
    QSystemTrayIcon, QMenu, QDateTimeEdit, QAbstractItemView, QFrame, QHeaderView)

from .categories import category_for
from .engine import DownloadManager, DownloadTask, GlobalLimiter, format_size, format_speed
from .grabber import fetch_links, probe_size
from .i18n import tr
from .settings import Settings, data_dir

URL_RE = re.compile(r"https?://\S+")

GLASS_CARD = """
QFrame#glass { background: rgba(18, 28, 58, 165); border: 1px solid rgba(255,255,255,110);
  border-top: 1px solid rgba(255,255,255,200); border-radius: 18px; }
QPushButton { background: rgba(255,255,255,38); color: white; border: 1px solid rgba(255,255,255,110);
  border-radius: 12px; padding: 7px 14px; }
QPushButton:hover { background: rgba(255,255,255,70); }
QPushButton:pressed { background: rgba(255,255,255,95); }
QLineEdit, QComboBox, QSpinBox, QDateTimeEdit { background: rgba(255,255,255,28); color: white;
  border: 1px solid rgba(255,255,255,90); border-radius: 10px; padding: 6px; }
QLabel { color: white; }
QTableWidget { background: rgba(12, 20, 45, 150); color: white; gridline-color: rgba(255,255,255,40);
  border: 1px solid rgba(255,255,255,80); border-radius: 14px; }
QHeaderView::section { background: rgba(255,255,255,30); color: white; border: none; padding: 6px; }
QTabWidget::pane { border: none; }
QTabBar::tab { background: rgba(255,255,255,30); color: white; border-radius: 12px; padding: 8px 16px; margin: 2px; }
QTabBar::tab:selected { background: rgba(140,170,255,90); }
"""

class AnimatedBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.phase = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(120)
    def _tick(self):
        self.phase += 0.02
        self.update()
    def paintEvent(self, event):
        p = QPainter(self)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        t = (math.sin(self.phase) + 1) / 2
        grad.setColorAt(0.0, QColor(10, 25, 90))
        grad.setColorAt(0.4 + 0.1 * t, QColor(95, 45, 170))
        grad.setColorAt(1.0, QColor(10, 130, 140))
        p.fillRect(self.rect(), QBrush(grad))

class SegmentBar(QWidget):
    def __init__(self, task=None):
        super().__init__()
        self.task = task
        self.setMinimumHeight(18)
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)
        p.setBrush(QColor(255, 255, 255, 35))
        p.setPen(QColor(255, 255, 255, 90))
        p.drawRoundedRect(r, 9, 9)
        if not self.task or not self.task.total or not self.task.segments:
            return
        total = self.task.total
        x = float(r.x())
        colors = [QColor(90, 170, 255), QColor(160, 110, 255), QColor(60, 220, 200), QColor(255, 170, 90)]
        for i, seg in enumerate(self.task.segments):
            w = r.width() * (seg.downloaded / total) if total else 0
            if w > 0:
                p.setBrush(colors[i % len(colors)])
                p.setPen(Qt.NoPen)
                p.drawRect(int(x), r.y(), int(w), r.height())
            x += r.width() * (seg.size / total) if total else 0
        # Glossy highlight stripe
        p.setBrush(QColor(255, 255, 255, 70))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(r.x() + 3, r.y() + 2, r.width() - 6, 5, 2, 2)

class AddDialog(QDialog):
    def __init__(self, parent, settings, prefill=""):
        super().__init__(parent)
        self.settings = settings
        self.lang = settings.get("language", "bn")
        self.setWindowTitle(tr(self.lang, "add_url"))
        self.setMinimumWidth(520)
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.url_edit = QLineEdit(prefill)
        self.name_edit = QLineEdit()
        self.dest_edit = QLineEdit(str(Path(settings.get("base_folder")) / "Other"))
        browse = QPushButton(tr(self.lang, "browse"))
        browse.clicked.connect(self._browse)
        dest_row = QHBoxLayout(); dest_row.addWidget(self.dest_edit); dest_row.addWidget(browse)
        self.conn = QComboBox(); self.conn.addItems(["1", "4", "8", "16", "32"])
        self.conn.setCurrentText(str(settings.get("default_connections", 8)))
        self.sched = QDateTimeEdit(); self.sched.setCalendarPopup(True)
        self.sched.setDateTime(QDateTime.currentDateTime())
        self.sched_check = QCheckBox(tr(self.lang, "scheduled_start"))
        form.addRow(tr(self.lang, "url"), self.url_edit)
        form.addRow(tr(self.lang, "filename"), self.name_edit)
        form.addRow(tr(self.lang, "destination"), dest_row)
        form.addRow(tr(self.lang, "connections"), self.conn)
        lay.addLayout(form)
        adv_btn = QPushButton(tr(self.lang, "advanced"))
        lay.addWidget(adv_btn)
        self.adv = QFrame(); self.adv.setVisible(False)
        aform = QFormLayout(self.adv)
        self.ua_edit = QLineEdit(); self.ref_edit = QLineEdit(); self.cookie_edit = QLineEdit()
        aform.addRow(tr(self.lang, "user_agent"), self.ua_edit)
        aform.addRow(tr(self.lang, "referer"), self.ref_edit)
        aform.addRow(tr(self.lang, "cookie"), self.cookie_edit)
        self.adv.setLayout(aform); lay.addWidget(self.adv)
        adv_btn.clicked.connect(lambda: self.adv.setVisible(not self.adv.isVisible()))
        lay.addWidget(self.sched_check); lay.addWidget(self.sched)
        btns = QHBoxLayout()
        ok = QPushButton(tr(self.lang, "add")); cancel = QPushButton(tr(self.lang, "cancel_btn"))
        ok.clicked.connect(self.accept); cancel.clicked.connect(self.reject)
        btns.addWidget(ok); btns.addWidget(cancel); lay.addLayout(btns)
        self.url_edit.textChanged.connect(self._on_url)
        self._on_url()
    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, tr(self.lang, "destination"))
        if d:
            self.dest_edit.setText(d)
    def _on_url(self):
        url = self.url_edit.text().strip()
        if url and not self.name_edit.text():
            name = url.rstrip("/").rsplit("/", 1)[-1].split("?")[0]
            if name:
                self.name_edit.setText(name)
                cat = category_for(name)
                self.dest_edit.setText(str(Path(self.settings.get("base_folder")) / cat))
    def values(self):
        headers = {}
        if self.ua_edit.text(): headers["User-Agent"] = self.ua_edit.text()
        if self.ref_edit.text(): headers["Referer"] = self.ref_edit.text()
        if self.cookie_edit.text(): headers["Cookie"] = self.cookie_edit.text()
        sched = self.sched.dateTime().toSecsSinceEpoch() if self.sched_check.isChecked() else None
        return {"url": self.url_edit.text().strip(), "filename": self.name_edit.text().strip() or None,
                "dest_dir": self.dest_edit.text().strip(), "connections": int(self.conn.currentText()),
                "headers": headers, "scheduled_at": sched}

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.lang = self.settings.get("language", "bn")
        self.setWindowTitle("TNxIDM")
        self.resize(980, 620)
        self.limiter = GlobalLimiter(self.settings.get("speed_limit_kbps", 0))
        self.manager = DownloadManager(data_dir() / "state.json", limiter=self.limiter, on_change=self._schedule_refresh)
        self.manager.max_concurrent = int(self.settings.get("max_concurrent", 2))
        self.manager.start_scheduler(20)
        self._done_seen = {t.id for t in self.manager.tasks if t.status == "done"}
        self._clip_seen = set()
        bg = AnimatedBackground(self)
        self.setCentralWidget(bg)
        root = QVBoxLayout(bg)
        self.setStyleSheet("QMainWindow { background: transparent; }" + GLASS_CARD)
        top = QHBoxLayout()
        self.add_btn = QPushButton(tr(self.lang, "add_url")); self.add_btn.clicked.connect(self._add_dialog)
        self.pause_all_btn = QPushButton(tr(self.lang, "pause_all")); self.pause_all_btn.clicked.connect(self.manager.pause_all)
        self.resume_all_btn = QPushButton(tr(self.lang, "resume_all")); self.resume_all_btn.clicked.connect(self.manager.resume_all)
        self.search = QLineEdit(); self.search.setPlaceholderText(tr(self.lang, "search"))
        self.search.textChanged.connect(self.refresh)
        self.total_label = QLabel("")
        top.addWidget(self.add_btn); top.addWidget(self.pause_all_btn); top.addWidget(self.resume_all_btn)
        top.addWidget(self.search); top.addWidget(self.total_label)
        root.addLayout(top)
        self.tabs = QTabWidget()
        self.dl_table = self._table([tr(self.lang, "filename"), tr(self.lang, "status"), tr(self.lang, "size"), tr(self.lang, "speed"), tr(self.lang, "eta"), tr(self.lang, "progress")])
        self.done_table = self._table([tr(self.lang, "filename"), tr(self.lang, "size"), tr(self.lang, "url")])
        self.tabs.addTab(self.dl_table, tr(self.lang, "downloads"))
        self.tabs.addTab(self.done_table, tr(self.lang, "completed"))
        grab = self._grabber_tab()
        self.tabs.addTab(grab, tr(self.lang, "grabber"))
        sett = self._settings_tab()
        self.tabs.addTab(sett, tr(self.lang, "settings"))
        root.addWidget(self.tabs)
        # Active-download actions (act on the selected Downloads row)
        active_acts = QHBoxLayout()
        for key, fn in [(tr(self.lang, "pause"), self._pause_sel), (tr(self.lang, "resume"), self._resume_sel),
                        (tr(self.lang, "cancel"), self._cancel_sel), (tr(self.lang, "retry"), self._retry_sel),
                        (tr(self.lang, "restart"), self._restart_sel)]:
            b = QPushButton(key); b.clicked.connect(fn); active_acts.addWidget(b)
        root.addLayout(active_acts)
        # Completed actions
        acts = QHBoxLayout()
        for key, fn in [(tr(self.lang, "open"), self._open_file), (tr(self.lang, "open_folder"), self._open_folder),
                        (tr(self.lang, "delete"), self._delete_done), (tr(self.lang, "copy_url"), self._copy_url),
                        (tr(self.lang, "redownload"), self._redownload)]:
            b = QPushButton(key); b.clicked.connect(fn); acts.addWidget(b)
        root.addLayout(acts)
        self._setup_tray()
        self.refresh_timer = QTimer(self); self.refresh_timer.timeout.connect(self.refresh); self.refresh_timer.start(800)
        self.clip_timer = QTimer(self); self.clip_timer.timeout.connect(self._check_clipboard); self.clip_timer.start(1500)
        self.refresh()
    def _table(self, headers):
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        return t
    def _schedule_refresh(self):
        QTimer.singleShot(0, self.refresh)
    def _grabber_tab(self):
        w = QWidget(); lay = QVBoxLayout(w)
        lay.addWidget(QLabel(tr(self.lang, "grabber_note")))
        self.grab_url = QLineEdit(); self.grab_url.setPlaceholderText(tr(self.lang, "page_url"))
        fetch = QPushButton(tr(self.lang, "grabber_fetch")); fetch.clicked.connect(self._fetch_grabber)
        self.grab_table = QTableWidget(0, 3); self.grab_table.setHorizontalHeaderLabels(["✓", tr(self.lang, "filename"), tr(self.lang, "size")])
        self.grab_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        add = QPushButton(tr(self.lang, "grabber_add_selected")); add.clicked.connect(self._add_grabbed)
        lay.addWidget(self.grab_url); lay.addWidget(fetch); lay.addWidget(self.grab_table); lay.addWidget(add)
        return w
    def _settings_tab(self):
        w = QWidget(); form = QFormLayout(w)
        self.conn_spin = QComboBox(); self.conn_spin.addItems(["1", "4", "8", "16", "32"]); self.conn_spin.setCurrentText(str(self.settings.get("default_connections", 8)))
        self.conc_spin = QSpinBox(); self.conc_spin.setRange(1, 10); self.conc_spin.setValue(int(self.settings.get("max_concurrent", 2)))
        self.limit_spin = QSpinBox(); self.limit_spin.setRange(0, 1000000); self.limit_spin.setValue(int(self.settings.get("speed_limit_kbps", 0)))
        self.base_edit = QLineEdit(str(self.settings.get("base_folder")))
        self.clip_check = QCheckBox(); self.clip_check.setChecked(bool(self.settings.get("clipboard_monitor", True)))
        self.tray_check = QCheckBox(); self.tray_check.setChecked(bool(self.settings.get("minimize_to_tray", True)))
        self.lang_combo = QComboBox(); self.lang_combo.addItems(["bn", "en"]); self.lang_combo.setCurrentText(self.lang)
        save = QPushButton(tr(self.lang, "save")); save.clicked.connect(self._save_settings)
        form.addRow(tr(self.lang, "default_connections"), self.conn_spin)
        form.addRow(tr(self.lang, "max_concurrent"), self.conc_spin)
        form.addRow(tr(self.lang, "speed_limit"), self.limit_spin)
        form.addRow(tr(self.lang, "base_folder"), self.base_edit)
        form.addRow(tr(self.lang, "clipboard_monitor"), self.clip_check)
        form.addRow(tr(self.lang, "minimize_to_tray"), self.tray_check)
        form.addRow(tr(self.lang, "language"), self.lang_combo)
        form.addRow(QLabel(tr(self.lang, "clipboard_note")))
        form.addRow(save)
        return w
    def _save_settings(self):
        self.settings.set("default_connections", int(self.conn_spin.currentText()))
        self.settings.set("max_concurrent", self.conc_spin.value())
        self.settings.set("speed_limit_kbps", self.limit_spin.value())
        self.settings.set("base_folder", self.base_edit.text())
        self.settings.set("clipboard_monitor", self.clip_check.isChecked())
        self.settings.set("minimize_to_tray", self.tray_check.isChecked())
        self.settings.set("language", self.lang_combo.currentText())
        self.lang = self.lang_combo.currentText()
        self.manager.max_concurrent = self.conc_spin.value()
        self.limiter.set_rate(self.limit_spin.value())
        self.manager.pump()
        QMessageBox.information(self, "TNxIDM", tr(self.lang, "save"))
    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = None; return
        self.tray = QSystemTrayIcon(self)
        # No proprietary icon is bundled; Qt's default/empty icon is used.
        menu = QMenu()
        for label, fn in [(tr(self.lang, "open"), self.show), (tr(self.lang, "add_url"), self._add_dialog),
                          (tr(self.lang, "pause_all"), self.manager.pause_all), (tr(self.lang, "resume_all"), self.manager.resume_all)]:
            a = QAction(label, self); a.triggered.connect(fn); menu.addAction(a)
        quit_a = QAction("Exit", self); quit_a.triggered.connect(QApplication.quit); menu.addAction(quit_a)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda r: self.show() if r == QSystemTrayIcon.DoubleClick else None)
        self.tray.show()
    def closeEvent(self, event):
        if self.settings.get("minimize_to_tray", True) and self.tray:
            event.ignore(); self.hide()
        else:
            self.manager.stop_scheduler(); event.accept()
    def _clipboard_text(self):
        try:
            return QApplication.clipboard().text() or ""
        except Exception:
            return ""
    def _add_dialog(self, prefill=""):
        if not prefill:
            m = URL_RE.search(self._clipboard_text())
            prefill = m.group(0) if m else ""
        dlg = AddDialog(self, self.settings, prefill)
        if dlg.exec():
            v = dlg.values()
            if not v["url"]:
                QMessageBox.warning(self, "TNxIDM", tr(self.lang, "no_url")); return
            dest = v["dest_dir"]
            if v["filename"]:
                dest = str(Path(self.settings.get("base_folder")) / category_for(v["filename"]))
                # Keep the dialog's folder if the user changed it deliberately is
                # approximated by using the category folder for new downloads.
            task = DownloadTask(v["url"], dest, v["filename"], v["connections"], v["headers"], v["scheduled_at"], state_dir=str(data_dir()))
            if v["scheduled_at"]:
                task.status = "scheduled"
            self.manager.add(task)
    def _check_clipboard(self):
        if not self.settings.get("clipboard_monitor", True):
            return
        text = self._clipboard_text().strip()
        m = URL_RE.search(text)
        if not m:
            return
        url = m.group(0)
        if url in self._clip_seen:
            return
        ext = url.rsplit(".", 1)[-1].lower().split("?")[0] if "." in url else ""
        from .categories import downloadable_extensions
        if ext not in downloadable_extensions():
            return
        self._clip_seen.add(url)
        if QMessageBox.question(self, "TNxIDM", tr(self.lang, "clipboard_prompt")) == QMessageBox.Yes:
            self._add_dialog(prefill=url)
    def _fetch_grabber(self):
        url = self.grab_url.text().strip()
        if not url:
            return
        try:
            links = fetch_links(url)
        except Exception as e:
            QMessageBox.warning(self, "TNxIDM", str(e)); return
        self.grab_table.setRowCount(0)
        for link in links:
            size = probe_size(link["url"])
            row = self.grab_table.rowCount(); self.grab_table.insertRow(row)
            chk = QCheckBox(); chk.setChecked(True)
            self.grab_table.setCellWidget(row, 0, chk)
            self.grab_table.setItem(row, 1, QTableWidgetItem(link["filename"]))
            self.grab_table.setItem(row, 2, QTableWidgetItem(format_size(size) if size else "?"))
            self.grab_table.item(row, 1).setData(Qt.UserRole, link["url"])
    def _add_grabbed(self):
        for row in range(self.grab_table.rowCount()):
            chk = self.grab_table.cellWidget(row, 0)
            if chk and chk.isChecked():
                item = self.grab_table.item(row, 1)
                url = item.data(Qt.UserRole) if item else None
                if url:
                    name = item.text()
                    dest = str(Path(self.settings.get("base_folder")) / category_for(name))
                    self.manager.add(DownloadTask(url, dest, name, int(self.settings.get("default_connections", 8)), state_dir=str(data_dir())))
    def _selected_active(self):
        row = self.dl_table.currentRow()
        if row < 0:
            return None
        active = [t for t in self.manager.tasks if t.status != "done"]
        q = self.search.text().strip().lower()
        if q:
            active = [t for t in active if q in (t.filename or "").lower() or q in t.url.lower()]
        return active[row] if row < len(active) else None
    def _pause_sel(self):
        t = self._selected_active()
        if t: self.manager.pause_task(t)
    def _resume_sel(self):
        t = self._selected_active()
        if t: self.manager.resume_task(t)
    def _cancel_sel(self):
        t = self._selected_active()
        if t: self.manager.cancel_task(t)
    def _retry_sel(self):
        t = self._selected_active()
        if t: self.manager.retry_task(t)
    def _restart_sel(self):
        t = self._selected_active()
        if t: self.manager.restart_task(t)
    def _selected_done(self):
        row = self.done_table.currentRow()
        if row < 0:
            return None
        done = [t for t in self.manager.tasks if t.status == "done"]
        q = self.search.text().strip().lower()
        if q:
            done = [t for t in done if q in (t.filename or "").lower() or q in t.url.lower()]
        return done[row] if row < len(done) else None
    def _open_file(self):
        t = self._selected_done()
        if t and t.dest_path.exists():
            self._open_path(str(t.dest_path))
    def _open_folder(self):
        t = self._selected_done()
        if t:
            self._open_path(str(t.dest_path.parent))
    def _open_path(self, path):
        if sys.platform.startswith("win"):
            os.startfile(path)  # noqa: S606 - user-selected local path only
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    def _delete_done(self):
        t = self._selected_done()
        if not t:
            return
        delete_file = QMessageBox.question(self, "TNxIDM", tr(self.lang, "delete_file_q")) == QMessageBox.Yes
        self.manager.remove_task(t, delete_file=delete_file)
    def _copy_url(self):
        t = self._selected_done()
        if t:
            QApplication.clipboard().setText(t.url)
    def _redownload(self):
        t = self._selected_done()
        if t:
            self.manager.add(DownloadTask(t.url, t.dest_dir, t.filename, t.connections, t.custom_headers, state_dir=str(data_dir())))
    def refresh(self):
        q = self.search.text().strip().lower()
        active = [t for t in self.manager.tasks if t.status != "done"]
        done = [t for t in self.manager.tasks if t.status == "done"]
        if q:
            active = [t for t in active if q in (t.filename or "").lower() or q in t.url.lower()]
            done = [t for t in done if q in (t.filename or "").lower() or q in t.url.lower()]
        self.dl_table.setRowCount(0)
        for t in active:
            row = self.dl_table.rowCount(); self.dl_table.insertRow(row)
            self.dl_table.setItem(row, 0, QTableWidgetItem(t.filename or t.url))
            status = tr(self.lang, {"downloading": "downloading", "paused": "paused", "failed": "failed", "scheduled": "scheduled"}.get(t.status, "queued"))
            if t.error and t.status == "failed":
                status += f" ({t.error[:60]})"
            self.dl_table.setItem(row, 1, QTableWidgetItem(status))
            self.dl_table.setItem(row, 2, QTableWidgetItem(f"{format_size(t.downloaded)} / {format_size(t.total) if t.total else '?'}"))
            self.dl_table.setItem(row, 3, QTableWidgetItem(format_speed(t.speed_bps)))
            self.dl_table.setItem(row, 4, QTableWidgetItem(t.eta))
            self.dl_table.setCellWidget(row, 5, SegmentBar(t))
        self.done_table.setRowCount(0)
        for t in done:
            row = self.done_table.rowCount(); self.done_table.insertRow(row)
            self.done_table.setItem(row, 0, QTableWidgetItem(t.filename or ""))
            self.done_table.setItem(row, 1, QTableWidgetItem(format_size(t.total) if t.total else "?"))
            self.done_table.setItem(row, 2, QTableWidgetItem(t.url))
        total = self.manager.total_speed()
        self.total_label.setText(f"{tr(self.lang, 'total_speed')}: {format_speed(total)}")
        if self.tray:
            self.tray.setToolTip(f"TNxIDM - {format_speed(total)}")
        for t in done:
            if t.id not in self._done_seen:
                self._done_seen.add(t.id)
                if self.tray:
                    self.tray.showMessage("TNxIDM", f"{tr(self.lang, 'download_complete')}: {t.filename}", QSystemTrayIcon.Information, 5000)

def run_gui():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()
