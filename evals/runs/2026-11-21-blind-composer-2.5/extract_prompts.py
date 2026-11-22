"""Extract id, category, and question only from golden_cases.py via AST."""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] if False else Path("/workspace")
source = (ROOT / "tests" / "golden_cases.py").read_text(encoding="utf-8")
module = ast.parse(source)
cases = []
for node in module.body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "CASES":
                if isinstance(node.value, ast.List):
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Dict):
                            row = {}
                            for k, v in zip(elt.keys, elt.values):
                                if k is None:
                                    continue
                                key = k.value
                                if key not in ("id", "category", "question"):
                                    continue
                                if isinstance(v, ast.Constant):
                                    row[key] = v.value
                            if "id" in row and "question" in row:
                                cases.append(row)
out = Path("/tmp/glovebox-eval-prompts.json")
out.write_text(json.dumps(cases, indent=2) + "\n", encoding="utf-8")
print(f"wrote {len(cases)} prompts to {out}")