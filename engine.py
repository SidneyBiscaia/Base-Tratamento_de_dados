from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile, uuid, zipfile
from datetime import datetime
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
PROJECTS_DIR = APP_DIR / "data" / "projects"
RUNNER_SCRIPT = APP_DIR / "runner.py"
DEFAULT_CONFIG = {"version": 2, "name": "Novo projeto", "inputs": [], "process_code": "", "output_code": "", "output_path": ""}

def slug(value: str) -> str:
    cleaned = "".join(c.lower() if c.isalnum() else "-" for c in value.strip())
    return "-".join(p for p in cleaned.split("-") if p)[:64] or "projeto"

def project_path(project_id: str) -> Path:
    if not project_id or Path(project_id).name != project_id:
        raise ValueError("Identificador de projeto inválido.")
    return PROJECTS_DIR / project_id

def list_projects() -> list[dict]:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    projects = []
    for path in PROJECTS_DIR.glob("*/project.json"):
        try:
            cfg = json.loads(path.read_text(encoding="utf-8"))
            projects.append({"id": path.parent.name, "name": cfg.get("name", path.parent.name)})
        except (OSError, json.JSONDecodeError):
            pass
    return sorted(projects, key=lambda item: item["name"].casefold())

def create_project(name: str) -> str:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    project_id = f"{slug(name)}-{uuid.uuid4().hex[:6]}"
    folder = project_path(project_id)
    folder.mkdir(parents=True)
    (folder / "inputs").mkdir()
    (folder / "runs").mkdir()
    save_config(project_id, {**DEFAULT_CONFIG, "name": name.strip() or "Novo projeto"})
    return project_id

def load_config(project_id: str) -> dict:
    path = project_path(project_id) / "project.json"
    if not path.exists():
        return dict(DEFAULT_CONFIG)
    data = json.loads(path.read_text(encoding="utf-8"))
    for key, value in DEFAULT_CONFIG.items():
        data.setdefault(key, value)
    return data

def save_config(project_id: str, config: dict) -> None:
    path = project_path(project_id) / "project.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)

def add_uploaded_files(project_id: str, input_id: str, files) -> list[str]:
    destination = project_path(project_id) / "inputs" / slug(input_id)
    destination.mkdir(parents=True, exist_ok=True)
    stored = []
    for uploaded in files:
        name = Path(uploaded.name).name
        if name and name not in {".", ".."}:
            target = destination / name
            target.write_bytes(uploaded.getvalue())
            stored.append(str(target))
    return stored

def ensure_demo_project() -> None:
    examples = [p for p in list_projects() if p["id"].startswith("exemplo-organizar-csv-")]
    project_id = examples[0]["id"] if examples else create_project("Exemplo Organizar CSV")
    folder = project_path(project_id)
    sample = folder / "inputs" / "movimentos.csv"
    if not sample.exists():
        sample.write_text("data,historico,valor\n2026-01-03,Recebimento cliente,1250.00\n2026-01-05,Taxa bancaria,-8.50\n2026-01-09,Pagamento fornecedor,-320.00\n", encoding="utf-8")
    config = load_config(project_id)
    is_old_demo = bool(config["inputs"]) and "INPUT_FILES_JSON" in config["inputs"][0].get("code", "")
    if config.get("demo_version") != 2 or is_old_demo:
        config["inputs"] = [{"id":"movimentos", "name":"Movimentos", "paths":[str(sample)], "code": '''import csv
result = []
for file_path in files:
    with file_path.open(encoding="utf-8-sig", newline="") as source:
        result.extend(dict(row) for row in csv.DictReader(source))'''}]
        config["process_code"] = ""
        config["output_code"] = '''import csv
records = data["Movimentos"]
columns = list(records[0]) if records else []
with (output_dir / "movimentos-organizados.csv").open("w", encoding="utf-8-sig", newline="") as destination:
    writer = csv.DictWriter(destination, fieldnames=columns)
    writer.writeheader()
    writer.writerows(records)'''
        config["demo_version"] = 2
        save_config(project_id, config)

def discover_files(paths: list[str]) -> list[Path]:
    found, seen = [], set()
    for raw in paths:
        path = Path(raw).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"Caminho não encontrado: {path}")
        candidates = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file() and not p.is_symlink() and not p.name.startswith("~$"))
        for candidate in candidates:
            resolved = candidate.resolve()
            key = str(resolved).casefold()
            if key not in seen:
                found.append(resolved)
                seen.add(key)
    if len(found) > 10000:
        raise ValueError("A entrada encontrou mais de 10.000 arquivos. Separe as fontes em grupos menores.")
    return found

def _run_block(run_dir: Path, block_name: str, code: str, context: dict, require_result: bool):
    if not code.strip():
        raise ValueError(f"O código da etapa “{block_name}” está vazio.")
    folder = run_dir / block_name
    folder.mkdir(parents=True, exist_ok=True)
    code_file, context_file, result_file = folder / "codigo.py", folder / "contexto.json", folder / "resultado.json"
    code_file.write_text(code, encoding="utf-8")
    context_file.write_text(json.dumps(context, ensure_ascii=False), encoding="utf-8")
    try:
        proc = subprocess.run([sys.executable, str(RUNNER_SCRIPT), str(code_file), str(context_file), str(result_file)], cwd=folder, env=os.environ.copy(), capture_output=True, text=True, timeout=300, check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"A etapa “{block_name}” ultrapassou cinco minutos e foi interrompida.") from exc
    stdout, stderr = (proc.stdout or "")[-12000:], (proc.stderr or "")[-12000:]
    if proc.returncode:
        raise RuntimeError(stderr or stdout or f"A etapa terminou com código {proc.returncode}.")
    if require_result:
        if not result_file.exists():
            raise RuntimeError(f"A etapa “{block_name}” terminou sem definir a variável `result`.")
        try:
            return json.loads(result_file.read_text(encoding="utf-8")), stdout
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"O resultado da etapa “{block_name}” não é JSON válido.") from exc
    return None, stdout

def run_project(project_id: str, selected_input_ids: list[str] | None = None, uploaded_files_by_input: dict[str, list] | None = None):
    config = load_config(project_id)
    if not config["inputs"]:
        raise ValueError("Adicione ao menos uma entrada antes de executar.")
    if selected_input_ids is None:
        selected_entries = config["inputs"]
    else:
        selected_set = set(selected_input_ids)
        selected_entries = [entry for entry in config["inputs"] if entry.get("id") in selected_set]
    if not selected_entries:
        raise ValueError("Selecione ao menos uma entrada para executar.")
    names = [entry.get("name", "").strip() for entry in selected_entries]
    if any(not name for name in names) or len(set(names)) != len(names):
        raise ValueError("As entradas selecionadas precisam ter nomes preenchidos e únicos.")
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
    run_dir = project_path(project_id) / "runs" / run_id
    run_dir.mkdir(parents=True)
    logs, entry_results = [], {}
    try:
        for index, entry in enumerate(selected_entries, start=1):
            name = entry["name"].strip()
            upload_temp = None
            try:
                if uploaded_files_by_input is None:
                    files = discover_files(entry.get("paths", []))
                else:
                    upload_temp = tempfile.TemporaryDirectory(prefix="data-engine-upload-")
                    upload_dir = Path(upload_temp.name)
                    files = []
                    seen_upload_names = set()
                    for uploaded in uploaded_files_by_input.get(entry.get("id", ""), []):
                        safe_name = Path(uploaded.name).name
                        if not safe_name or safe_name in {".", ".."} or safe_name.casefold() in seen_upload_names:
                            continue
                        seen_upload_names.add(safe_name.casefold())
                        target = upload_dir / safe_name
                        target.write_bytes(uploaded.getvalue())
                        files.append(target)
                if not files:
                    raise ValueError(f"A entrada “{name}” não encontrou arquivos.")
                result, stdout = _run_block(run_dir, f"entrada-{index}", entry.get("code", ""), {"stage":"input", "entry_name":name, "files":[str(p) for p in files]}, True)
            finally:
                if upload_temp is not None:
                    upload_temp.cleanup()
            entry_results[name] = result
            logs.append(f"Entrada: {name}\n{stdout}".rstrip())
        payload = entry_results
        if config.get("process_code", "").strip():
            payload, stdout = _run_block(run_dir, "processamento", config["process_code"], {"stage":"process", "inputs":entry_results}, True)
            logs.append(f"Processamento geral\n{stdout}".rstrip())
        data_file = run_dir / "dados.json"
        data_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        artifacts = run_dir / "resultados"
        artifacts.mkdir()
        if config.get("output_code", "").strip():
            _, stdout = _run_block(run_dir, "saida", config["output_code"], {"stage":"output", "data":payload, "output_dir":str(artifacts)}, False)
            logs.append(f"Saída final\n{stdout}".rstrip())
            if not any(p.is_file() for p in artifacts.rglob("*")):
                raise RuntimeError("A etapa de saída terminou, mas não criou arquivos em `output_dir`.")
        else:
            shutil.copy2(data_file, artifacts / "dados.json")
        artifact_files = sorted(path for path in artifacts.rglob("*") if path.is_file())
        if len(artifact_files) <= 4:
            download_files = artifact_files
        else:
            archive = run_dir / "resultados.zip"
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for path in artifact_files:
                    zf.write(path, path.relative_to(artifacts))
            download_files = [archive]
        destination = config.get("output_path", "").strip()
        if destination:
            output_folder = Path(destination).expanduser()
            output_folder.mkdir(parents=True, exist_ok=True)
            for path in artifacts.rglob("*"):
                if path.is_file():
                    target = output_folder / path.relative_to(artifacts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, target)
        _record_run(project_id, run_id, "concluído", "")
        return download_files, logs
    except Exception as exc:
        _record_run(project_id, run_id, "falhou", str(exc))
        raise

def _record_run(project_id: str, run_id: str, status: str, message: str) -> None:
    path = project_path(project_id) / "history.json"
    try:
        history = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    except json.JSONDecodeError:
        history = []
    history.insert(0, {"id":run_id, "status":status, "at":datetime.now().isoformat(timespec="seconds"), "message":message})
    path.write_text(json.dumps(history[:100], ensure_ascii=False, indent=2), encoding="utf-8")

def read_history(project_id: str) -> list[dict]:
    path = project_path(project_id) / "history.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
