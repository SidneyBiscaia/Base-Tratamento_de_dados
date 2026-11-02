import json
import sys
from pathlib import Path


def main() -> int:
    code_path, context_path, result_path = map(Path, sys.argv[1:4])
    context = json.loads(context_path.read_text(encoding="utf-8"))
    if context.get("stage") == "input":
        context["files"] = [Path(item) for item in context.get("files", [])]
    if context.get("stage") == "output":
        context["output_dir"] = Path(context["output_dir"])
    namespace = {"__name__": "__main__", "__file__": str(code_path), **context}
    source = code_path.read_text(encoding="utf-8")
    exec(compile(source, str(code_path), "exec"), namespace)
    if context.get("stage") in {"input", "process"}:
        if "result" not in namespace:
            raise RuntimeError("Defina a variável `result` com os dados produzidos por esta etapa.")
        result_path.write_text(json.dumps(namespace["result"], ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
