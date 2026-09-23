from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import zipfile
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, BooleanVar, IntVar, StringVar, TclError, Tk, Toplevel, filedialog, messagebox
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from levelupdiag_core.manifest import load_manifest, resolve_selection
from levelupdiag_core.runner import run_campaign
from run_medikristal_zip import find_target, safe_extract

APP_TITLE = "LevelUpDiag-MediKristal"
DEFAULT_TARGET = r"C:\mycode\MediKristal\MediKristal"
CAMPAIGNS = ("baseline", "software", "delivery", "release", "deep")
VERDICTS = (
    "PASS", "WARN", "FAIL", "SKIP", "BLOCKED", "PARTIAL",
    "ERROR", "INFRA_ERROR", "CONFIG_ERROR",
)


def is_medikristal_repo(path: Path) -> bool:
    path = Path(path)
    return (
        path.is_dir()
        and (path / "backend" / "pyproject.toml").is_file()
        and (path / "contracts" / "openapi.json").is_file()
    )


def normalize_target_path(path: Path) -> Path:
    path = Path(path)
    if path.name.lower() == ".git" and path.is_dir():
        return path.parent
    return path


def detect_target_kind(path: Path) -> str | None:
    path = normalize_target_path(Path(path))
    if is_medikristal_repo(path):
        return "repository"
    if path.is_file() and path.suffix.lower() == ".zip" and zipfile.is_zipfile(path):
        return "zip"
    return None


def open_path(path: Path) -> None:
    path = Path(path)
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def summary_text(summary: dict) -> str:
    lines = [
        f"{APP_TITLE} — {summary.get('selection', '')}",
        f"Verdict: {summary.get('verdict', 'UNKNOWN')}",
        f"Run: {summary.get('run_id', '')}",
        f"Target: {summary.get('target_repo_root', '')}",
        "",
    ]
    for row in summary.get("levels", []):
        lines.append(f"{row.get('id', ''):>4}  {row.get('verdict', ''):<12} {row.get('name', '')}")
    return "\n".join(lines)


class LevelUpDiagUI:
    def __init__(self, root: Tk):
        self.root = root
        self.tool_root = Path(__file__).resolve().parent
        self.events: queue.Queue[tuple[str, dict]] = queue.Queue()
        self.running = False
        self.current_summary: dict | None = None
        self.current_run_root: Path | None = None
        self.finished_levels = 0
        self.total_levels = 0

        self.target_var = StringVar(value=DEFAULT_TARGET)
        self.campaign_var = StringVar(value="release")
        self.jobs_var = IntVar(value=3)
        self.fail_fast_var = BooleanVar(value=False)
        self.output_var = StringVar(value=str(self.tool_root / "levelupdiag_zip_runs"))
        self.status_var = StringVar(value="Prêt")
        self.verdict_var = StringVar(value="—")
        self.counts_var = StringVar(value="Aucune validation exécutée")
        self.target_kind_var = StringVar(value="Cible non sélectionnée")

        self._configure_window()
        self._build_ui()
        self.root.after(100, self._drain_events)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_window(self) -> None:
        self.root.title(APP_TITLE)
        self.root.geometry("1120x760")
        self.root.minsize(900, 620)
        try:
            style = ttk.Style(self.root)
            if "vista" in style.theme_names():
                style.theme_use("vista")
            elif "clam" in style.theme_names():
                style.theme_use("clam")
            style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
            style.configure("Subtitle.TLabel", font=("Segoe UI", 10))
            style.configure("Verdict.TLabel", font=("Segoe UI", 18, "bold"))
            style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"))
        except Exception:
            pass

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill=BOTH, expand=True)

        ttk.Label(outer, text=APP_TITLE, style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            outer,
            text="Validation structurée d'un dépôt ou d'une archive MediKristal — sans réseau ni installation implicite.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(0, 12))

        target = ttk.LabelFrame(outer, text="Cible", padding=10)
        target.pack(fill=X)
        target.columnconfigure(0, weight=1)
        self.target_entry = ttk.Entry(target, textvariable=self.target_var)
        self.target_entry.grid(row=0, column=0, columnspan=4, sticky="ew", padx=(0, 8))
        ttk.Button(target, text="Dossier…", command=self._browse_folder).grid(row=0, column=4, padx=3)
        ttk.Button(target, text="ZIP…", command=self._browse_zip).grid(row=0, column=5, padx=3)
        ttk.Label(target, textvariable=self.target_kind_var).grid(row=1, column=0, columnspan=6, sticky="w", pady=(6, 0))
        self.target_entry.bind("<FocusOut>", lambda _e: self._refresh_target_kind())
        self.target_entry.bind("<Return>", lambda _e: self._refresh_target_kind())

        options = ttk.LabelFrame(outer, text="Exécution", padding=10)
        options.pack(fill=X, pady=(10, 0))
        ttk.Label(options, text="Campagne").grid(row=0, column=0, sticky="w")
        self.campaign_combo = ttk.Combobox(options, textvariable=self.campaign_var, values=CAMPAIGNS, state="readonly", width=14)
        self.campaign_combo.grid(row=0, column=1, padx=(6, 18), sticky="w")
        ttk.Label(options, text="Jobs").grid(row=0, column=2, sticky="w")
        self.jobs_spin = ttk.Spinbox(options, from_=1, to=16, textvariable=self.jobs_var, width=5)
        self.jobs_spin.grid(row=0, column=3, padx=(6, 18), sticky="w")
        self.fail_fast_check = ttk.Checkbutton(options, text="Fail-fast", variable=self.fail_fast_var)
        self.fail_fast_check.grid(row=0, column=4, sticky="w")
        options.columnconfigure(5, weight=1)
        self.run_button = ttk.Button(options, text="Lancer la validation", command=self._start_validation, style="Primary.TButton")
        self.run_button.grid(row=0, column=6, padx=(12, 0), sticky="e")

        ttk.Label(options, text="Sortie des preuves pour une cible ZIP").grid(row=1, column=0, columnspan=2, sticky="w", pady=(9, 0))
        self.output_entry = ttk.Entry(options, textvariable=self.output_var)
        self.output_entry.grid(row=1, column=2, columnspan=4, sticky="ew", padx=(6, 8), pady=(9, 0))
        ttk.Button(options, text="Choisir…", command=self._browse_output).grid(row=1, column=6, sticky="e", pady=(9, 0))

        state = ttk.Frame(outer)
        state.pack(fill=X, pady=(12, 6))
        ttk.Label(state, text="Verdict", font=("Segoe UI", 9)).pack(side=LEFT)
        self.verdict_label = ttk.Label(state, textvariable=self.verdict_var, style="Verdict.TLabel")
        self.verdict_label.pack(side=LEFT, padx=(8, 18))
        ttk.Label(state, textvariable=self.counts_var).pack(side=LEFT)
        ttk.Label(state, textvariable=self.status_var).pack(side=RIGHT)

        self.progress = ttk.Progressbar(outer, mode="determinate", maximum=100, value=0)
        self.progress.pack(fill=X, pady=(0, 10))

        actions = ttk.Frame(outer)
        actions.pack(fill=X, pady=(0, 7))
        self.open_folder_button = ttk.Button(actions, text="Ouvrir les preuves", command=self._open_report_folder, state="disabled")
        self.open_folder_button.pack(side=LEFT)
        self.open_summary_button = ttk.Button(actions, text="Ouvrir summary.json", command=self._open_summary, state="disabled")
        self.open_summary_button.pack(side=LEFT, padx=(6, 0))
        self.copy_button = ttk.Button(actions, text="Copier le résumé", command=self._copy_summary, state="disabled")
        self.copy_button.pack(side=LEFT, padx=(6, 0))
        ttk.Label(actions, text="Double-cliquer un niveau pour voir ses findings.").pack(side=RIGHT)

        pane = ttk.Panedwindow(outer, orient="vertical")
        pane.pack(fill=BOTH, expand=True)

        results_frame = ttk.LabelFrame(pane, text="Niveaux", padding=6)
        log_frame = ttk.LabelFrame(pane, text="Journal", padding=6)
        pane.add(results_frame, weight=3)
        pane.add(log_frame, weight=2)

        self.tree = ttk.Treeview(results_frame, columns=("id", "verdict", "name"), show="headings", height=12)
        self.tree.heading("id", text="ID")
        self.tree.heading("verdict", text="Verdict")
        self.tree.heading("name", text="Niveau")
        self.tree.column("id", width=90, anchor="center", stretch=False)
        self.tree.column("verdict", width=130, anchor="center", stretch=False)
        self.tree.column("name", width=700, anchor="w")
        ybar = ttk.Scrollbar(results_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ybar.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        ybar.pack(side=RIGHT, fill=Y)
        self.tree.bind("<Double-1>", self._show_level_details)

        self.log = ScrolledText(log_frame, wrap="word", height=10, font=("Consolas", 9), state="disabled")
        self.log.pack(fill=BOTH, expand=True)

    def _browse_folder(self) -> None:
        value = filedialog.askdirectory(title="Choisir le dépôt MediKristal")
        if value:
            self.target_var.set(value)
            self._refresh_target_kind()

    def _browse_zip(self) -> None:
        value = filedialog.askopenfilename(title="Choisir une archive MediKristal", filetypes=[("Archives ZIP", "*.zip"), ("Tous les fichiers", "*.*")])
        if value:
            self.target_var.set(value)
            self._refresh_target_kind()

    def _browse_output(self) -> None:
        value = filedialog.askdirectory(title="Choisir le dossier de sortie")
        if value:
            self.output_var.set(value)

    def _refresh_target_kind(self) -> None:
        raw = self.target_var.get().strip()
        if not raw:
            self.target_kind_var.set("Cible non sélectionnée")
            return
        kind = detect_target_kind(Path(raw).expanduser())
        if kind == "repository":
            self.target_kind_var.set("Dépôt MediKristal détecté")
        elif kind == "zip":
            self.target_kind_var.set("Archive ZIP détectée — extraction temporaire sécurisée")
        else:
            self.target_kind_var.set("Cible invalide : sélectionner la racine MediKristal ou un ZIP valide")

    def _start_validation(self) -> None:
        if self.running:
            return
        raw = self.target_var.get().strip()
        target = Path(raw).expanduser() if raw else Path()
        kind = detect_target_kind(target)
        target = normalize_target_path(target)
        if kind is None:
            messagebox.showerror(APP_TITLE, "Sélectionne la racine d'un dépôt MediKristal ou une archive ZIP valide.")
            return
        try:
            jobs = int(self.jobs_var.get())
        except (TypeError, ValueError, TclError):
            jobs = 3
        if not 1 <= jobs <= 16:
            messagebox.showerror(APP_TITLE, "Le nombre de jobs doit être compris entre 1 et 16.")
            return
        output_root = Path(self.output_var.get().strip() or (self.tool_root / "levelupdiag_zip_runs")).expanduser()

        self.running = True
        self.current_summary = None
        self.current_run_root = None
        self.finished_levels = 0
        self.total_levels = 0
        self.verdict_var.set("RUNNING")
        self.counts_var.set("Validation en cours")
        self.status_var.set("Initialisation…")
        self.progress.configure(value=0, maximum=100)
        self._clear_tree()
        self._clear_log()
        self._append_log(f"Cible: {target}")
        self._append_log(f"Campagne: {self.campaign_var.get()} | jobs={jobs} | fail-fast={self.fail_fast_var.get()}")
        self._set_controls_enabled(False)

        worker = threading.Thread(
            target=self._run_validation,
            args=(target.resolve(), kind, self.campaign_var.get(), jobs, self.fail_fast_var.get(), output_root.resolve()),
            daemon=True,
            name="levelupdiag-ui-runner",
        )
        worker.start()

    def _run_validation(self, target: Path, kind: str, campaign: str, jobs: int, fail_fast: bool, output_root: Path) -> None:
        try:
            if kind == "repository":
                summary, code, run_root = run_campaign(
                    self.tool_root,
                    campaign,
                    target_override=str(target),
                    jobs=jobs,
                    fail_fast=fail_fast,
                    progress_callback=self._progress_callback,
                )
                final_root = run_root
            else:
                output_root.mkdir(parents=True, exist_ok=True)
                with tempfile.TemporaryDirectory(prefix="levelupdiag-mk-ui-") as td:
                    extracted = Path(td) / "extracted"
                    extracted.mkdir()
                    self.events.put(("ui_log", {"message": "Extraction sécurisée de l'archive…"}))
                    safe_extract(target, extracted)
                    repo = find_target(extracted)
                    self.events.put(("ui_log", {"message": f"Dépôt détecté dans le ZIP: {repo.name}"}))
                    summary, code, run_root = run_campaign(
                        self.tool_root,
                        campaign,
                        target_override=str(repo),
                        jobs=jobs,
                        fail_fast=fail_fast,
                        progress_callback=self._progress_callback,
                    )
                    final_root = output_root / f"{target.stem}-{summary['run_id']}"
                    if final_root.exists():
                        shutil.rmtree(final_root)
                    shutil.copytree(run_root, final_root)
                    # The summary contains only relative result paths, so it remains portable.
                    summary = dict(summary)
                    summary["source_archive"] = str(target)
                    summary["evidence_root"] = str(final_root)
                    (final_root / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            self.events.put(("ui_finished", {"summary": summary, "code": code, "run_root": str(final_root)}))
        except Exception as exc:
            self.events.put(("ui_error", {"message": f"{type(exc).__name__}: {exc}"}))

    def _progress_callback(self, event: str, payload: dict) -> None:
        self.events.put((event, payload))

    def _drain_events(self) -> None:
        try:
            while True:
                event, payload = self.events.get_nowait()
                self._handle_event(event, payload)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._drain_events)

    def _handle_event(self, event: str, payload: dict) -> None:
        if event == "campaign_started":
            self.total_levels = int(payload.get("total", 0) or 0)
            self.finished_levels = 0
            self.progress.configure(maximum=max(1, self.total_levels), value=0)
            self.status_var.set(f"0/{self.total_levels} niveaux terminés")
            self._append_log(f"Run {payload.get('run_id')} démarré — {self.total_levels} niveaux")
            for lid in payload.get("levels", []):
                if not self.tree.exists(lid):
                    self.tree.insert("", END, iid=lid, values=(lid, "PENDING", ""))
        elif event == "level_started":
            lid = payload.get("level_id", "")
            name = payload.get("name", "")
            self._set_tree_row(lid, "RUNNING", name)
            self.status_var.set(f"{self.finished_levels}/{self.total_levels} — {lid} en cours")
            self._append_log(f"▶ {lid}  {name}")
        elif event == "level_finished":
            lid = payload.get("level_id", "")
            verdict = payload.get("verdict", "ERROR")
            name = payload.get("name", "")
            self.finished_levels += 1
            self._set_tree_row(lid, verdict, name)
            self.progress.configure(value=min(self.finished_levels, max(1, self.total_levels)))
            self.status_var.set(f"{self.finished_levels}/{self.total_levels} niveaux terminés")
            self._append_log(f"■ {lid}  {verdict:<12} {name}")
        elif event == "ui_log":
            self._append_log(payload.get("message", ""))
        elif event == "ui_finished":
            self._finish_success(payload["summary"], int(payload.get("code", 0)), Path(payload["run_root"]))
        elif event == "ui_error":
            self._finish_error(payload.get("message", "Erreur inconnue"))

    def _finish_success(self, summary: dict, code: int, run_root: Path) -> None:
        self.running = False
        self.current_summary = summary
        self.current_run_root = run_root
        self._populate_summary(summary)
        verdict = summary.get("verdict", "UNKNOWN")
        self.verdict_var.set(verdict)
        counts = summary.get("counts", {})
        visible = [f"{name} {counts.get(name, 0)}" for name in ("PASS", "WARN", "FAIL", "ERROR", "INFRA_ERROR", "BLOCKED") if counts.get(name, 0)]
        self.counts_var.set(" · ".join(visible) if visible else "Aucun résultat")
        self.progress.configure(value=max(1, self.total_levels))
        self.status_var.set(f"Terminé — code {code}")
        self._append_log(f"Campagne terminée: {verdict} (code {code})")
        self._append_log(f"Preuves: {run_root}")
        self._set_controls_enabled(True)
        self.open_folder_button.configure(state="normal")
        self.open_summary_button.configure(state="normal")
        self.copy_button.configure(state="normal")

    def _finish_error(self, message: str) -> None:
        self.running = False
        self.verdict_var.set("ERROR")
        self.counts_var.set("Échec du lanceur")
        self.status_var.set("Erreur")
        self._append_log(f"ERREUR: {message}")
        self._set_controls_enabled(True)
        messagebox.showerror(APP_TITLE, message)

    def _populate_summary(self, summary: dict) -> None:
        self._clear_tree()
        for row in summary.get("levels", []):
            self._set_tree_row(row.get("id", ""), row.get("verdict", ""), row.get("name", ""))

    def _set_tree_row(self, lid: str, verdict: str, name: str) -> None:
        if not lid:
            return
        values = (lid, verdict, name)
        if self.tree.exists(lid):
            self.tree.item(lid, values=values)
        else:
            self.tree.insert("", END, iid=lid, values=values)

    def _clear_tree(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert(END, text.rstrip() + "\n")
        self.log.see(END)
        self.log.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", END)
        self.log.configure(state="disabled")

    def _set_controls_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.target_entry.configure(state=state)
        self.jobs_spin.configure(state=state)
        self.fail_fast_check.configure(state=state)
        self.output_entry.configure(state=state)
        self.run_button.configure(state=state)
        self.campaign_combo.configure(state="readonly" if enabled else "disabled")
        if not enabled:
            self.open_folder_button.configure(state="disabled")
            self.open_summary_button.configure(state="disabled")
            self.copy_button.configure(state="disabled")

    def _open_report_folder(self) -> None:
        if self.current_run_root and self.current_run_root.exists():
            try:
                open_path(self.current_run_root)
            except Exception as exc:
                messagebox.showerror(APP_TITLE, f"Impossible d'ouvrir le dossier: {exc}")

    def _open_summary(self) -> None:
        if self.current_run_root:
            path = self.current_run_root / "summary.json"
            if path.exists():
                try:
                    open_path(path)
                except Exception as exc:
                    messagebox.showerror(APP_TITLE, f"Impossible d'ouvrir le résumé: {exc}")

    def _copy_summary(self) -> None:
        if not self.current_summary:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(summary_text(self.current_summary))
        self.status_var.set("Résumé copié dans le presse-papiers")

    def _show_level_details(self, _event=None) -> None:
        if not self.current_summary or not self.current_run_root:
            return
        selected = self.tree.selection()
        if not selected:
            return
        lid = selected[0]
        row = next((x for x in self.current_summary.get("levels", []) if x.get("id") == lid), None)
        if not row:
            return
        path = self.current_run_root / row.get("result", "")
        if not path.is_file():
            messagebox.showwarning(APP_TITLE, f"Résultat introuvable pour {lid}.")
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Impossible de lire {path.name}: {exc}")
            return

        win = Toplevel(self.root)
        win.title(f"{lid} — {row.get('name', '')}")
        win.geometry("900x620")
        body = ttk.Frame(win, padding=12)
        body.pack(fill=BOTH, expand=True)
        ttk.Label(body, text=f"{lid} — {data.get('level_name', row.get('name', ''))}", style="Title.TLabel").pack(anchor="w")
        ttk.Label(body, text=f"Verdict: {data.get('verdict', 'UNKNOWN')}   |   {data.get('purpose', '')}", wraplength=850).pack(anchor="w", pady=(4, 10))
        text = ScrolledText(body, wrap="word", font=("Consolas", 9))
        text.pack(fill=BOTH, expand=True)
        findings = data.get("findings", [])
        if not findings:
            text.insert(END, "Aucun finding.\n")
        for finding in findings:
            text.insert(END, f"[{finding.get('verdict', '')}] {finding.get('id', '')}\n")
            text.insert(END, f"{finding.get('message', '')}\n")
            if finding.get("recommendation"):
                text.insert(END, f"Recommandation: {finding['recommendation']}\n")
            if finding.get("path"):
                text.insert(END, f"Chemin: {finding['path']}\n")
            if finding.get("evidence") is not None:
                text.insert(END, "Evidence:\n" + json.dumps(finding["evidence"], indent=2, ensure_ascii=False) + "\n")
            text.insert(END, "\n")
        text.configure(state="disabled")
        ttk.Button(body, text="Fermer", command=win.destroy).pack(anchor="e", pady=(8, 0))

    def _on_close(self) -> None:
        if self.running:
            messagebox.showinfo(APP_TITLE, "Une validation est en cours. La fermeture est désactivée jusqu'à la fin de la campagne.")
            return
        self.root.destroy()


def main() -> int:
    root = Tk()
    LevelUpDiagUI(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
