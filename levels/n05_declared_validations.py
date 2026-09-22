from __future__ import annotations
import os
from pathlib import Path
from levelupdiag_core.commands import normalize_command, run_command


def run(cfg, report):
    validators=[v for v in cfg.get("validators",[]) if v.get("enabled",True)]
    if not validators:
        report.add("validators.declared.present", "PASS", "validation", "No validators are declared; the neutral frame correctly executed no guessed target command.", recommendation="Declare real public validators only if deeper target validation is required.")
        return
    target=Path(cfg["_target_root"]); execution=cfg.get("execution",{}); limit=execution.get("capture_limit_kb",256)
    for v in validators:
        vid=v.get("id") or "unnamed"
        name=v.get("name") or vid
        required=bool(v.get("required",False))
        if v.get("mutates_target",False) and not execution.get("allow_target_mutation",False):
            report.add(f"validator.{vid}.mutation_policy", "BLOCKED" if required else "WARN", "validation", f"Validator '{name}' is declared as target-mutating and mutation is disabled.")
            continue
        if v.get("network",False) and not execution.get("allow_network",False):
            report.add(f"validator.{vid}.network_policy", "BLOCKED" if required else "WARN", "validation", f"Validator '{name}' requires network access and network-enabled validators are disabled.")
            continue
        cwd=(target / v.get("cwd", ".")).resolve(strict=False)
        if not cwd.is_relative_to(target) or not cwd.is_dir():
            report.add(f"validator.{vid}.cwd", "CONFIG_ERROR", "validation", f"Validator '{name}' has an invalid working directory.", evidence=str(cwd)); continue
        command=v.get("command")
        if not command:
            report.add(f"validator.{vid}.command", "CONFIG_ERROR", "validation", f"Validator '{name}' has no command."); continue
        timeout=int(v.get("timeout_seconds",execution.get("default_timeout_seconds",120)))
        try:
            env = os.environ.copy()
            for key, value in (v.get("env") or {}).items():
                env[str(key)] = str(value)
            result=run_command(command,cwd=cwd,timeout_seconds=timeout,capture_limit_kb=limit,env=env,redact_output=cfg.get("redaction",{}).get("enabled",True))
        except (FileNotFoundError, PermissionError, OSError) as e:
            report.add(f"validator.{vid}.executable", "BLOCKED" if required else "WARN", "validation", f"Validator '{name}' could not be launched.", evidence=f"{type(e).__name__}: {e}")
            continue
        if result["timed_out"]:
            verdict="INFRA_ERROR"
        elif result["exit_code"]==0:
            verdict="PASS"
        else:
            verdict="FAIL" if required else "WARN"
        report.add(f"validator.{vid}.result", verdict, "validation", f"Validator '{name}' completed." if not result["timed_out"] else f"Validator '{name}' timed out.", evidence=result, recommendation=None if verdict=="PASS" else "Inspect the validator output and target-specific documentation.")
