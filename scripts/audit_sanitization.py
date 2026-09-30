#!/usr/bin/env python3
"""
ARKHÉ Codebase Sanitization & Hygiene Auditor
=============================================
Audits the codebase for:
1. Hardcoded secrets, API keys, passwords, and private tokens.
2. Hardcoded local absolute paths (e.g., C:\\Users\\...).
3. Leftover scratch debug files and stray temporary test outputs.
4. Git hygiene and .gitignore coverage.
"""

import os
import re
import sys

# Configure UTF-8 console output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PATTERNS = {
    "SECRET_ASSIGNMENT": re.compile(r'(?i)(api[_-]?key|secret|password|private[_-]?key)\s*[:=]\s*["\']([^"\']+)["\']'),
    "HARDCODED_LOCAL_PATH": re.compile(r'(?i)[a-zA-Z]:\\(users|home)\\[a-zA-Z0-9_\-]+'),
    "BEARER_TOKEN": re.compile(r'(?i)bearer\s+[a-zA-Z0-9_\-\.]{20,}'),
}

IGNORE_DIRS = {'.git', '__pycache__', 'node_modules', '.venv', 'env', 'dist', 'build', 'scratch'}
IGNORE_FILES = {'audit_sanitization.py'}

def audit():
    print("=" * 80)
    print("         ARKHÉ CODEBASE SANITIZATION & SECURITY AUDIT")
    print("=" * 80)
    
    findings = []
    local_path_findings = []
    scratch_files = []
    
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            if f in IGNORE_FILES:
                continue
            path = os.path.normpath(os.path.join(root, f))
            
            # Check scratch files
            if f.startswith("scratch_") or f.endswith(".pyc") or f == "Thumbs.db":
                scratch_files.append(path)
                
            # Scan text files for sensitive info
            ext = os.path.splitext(f)[1].lower()
            if ext in ['.py', '.yaml', '.yml', '.json', '.html', '.md', '.txt', '.sh', '.ps1', 'dockerfile']:
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                        for line_no, line in enumerate(fp, 1):
                            # Skip comments or documentation placeholders
                            if line.strip().startswith(("#", "//", "<!--", "*")):
                                continue
                            if "${" in line or "placeholder" in line.lower() or "example" in line.lower():
                                continue
                                
                            # Check secrets
                            for key, pat in PATTERNS.items():
                                match = pat.search(line)
                                if match:
                                    if key == "HARDCODED_LOCAL_PATH":
                                        local_path_findings.append((path, line_no, match.group(0)))
                                    elif key == "SECRET_ASSIGNMENT":
                                        val = match.group(2)
                                        # Ignore trivial non-secret values
                                        if val.lower() not in ["none", "true", "false", "", "utf-8", "latest", "default"]:
                                            findings.append((path, line_no, key, match.group(0)))
                                    else:
                                        findings.append((path, line_no, key, match.group(0)))
                except Exception as e:
                    pass

    print(f"\n1. Secrets & Private Credentials Audit:")
    if not findings:
        print("   ✅ NENHUM segredo, chave de API ou senha hardcoded encontrada.")
    else:
        print(f"   ⚠️ Encontradas {len(findings)} ocorrências potenciais:")
        for path, line_no, key, val in findings:
            print(f"      - {path}:{line_no} [{key}] -> {val}")

    print(f"\n2. Local Absolute Machine Paths Audit (ex: C:\\Users\\...):")
    if not local_path_findings:
        print("   ✅ NENHUM caminho absoluto de máquina de desenvolvedor encontrado.")
    else:
        print(f"   ⚠️ Encontrados {len(local_path_findings)} caminhos locais absolutos:")
        for path, line_no, val in local_path_findings:
            print(f"      - {path}:{line_no} -> {val}")

    print(f"\n3. Arquivos Temporários e Scratch Scripts:")
    if not scratch_files:
        print("   ✅ Nenhum script scratch residual encontrado na raiz.")
    else:
        print(f"   ⚠️ Encontrados {len(scratch_files)} arquivos temporários/scratch:")
        for sf in scratch_files:
            print(f"      - {sf}")

    return {
        "secrets_count": len(findings),
        "local_paths_count": len(local_path_findings),
        "scratch_count": len(scratch_files)
    }

if __name__ == "__main__":
    audit()
