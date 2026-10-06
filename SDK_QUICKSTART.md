# Instalação e demonstração dos SDKs alpha

Python3.10+; validação local em Python3.12. Trabalhe na raiz deste checkout.

## Windows PowerShell, ambiente novo

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install "setuptools>=77" wheel "pydantic>=2.7,<3"
.venv\Scripts\python.exe sdk/build.py
.venv\Scripts\python.exe trajectory-sdk/build.py
.venv\Scripts\python.exe -m pip install .review-build/defense-0.2.0/arkhe_defense_sdk-0.2.0-py3-none-any.whl .review-build/trajectory-0.2.0/arkhe_trajectory_sdk-0.2.0-py3-none-any.whl
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m examples.defense.pilot_demo --output-dir results/local-pilot-demo
```

## Linux/macOS

Use `python3 -m venv .venv`; substitua `.venv\Scripts\python.exe` por `.venv/bin/python` nos comandos acima. Não é necessário ativar o ambiente. `setuptools` e `wheel` são dependências de build; o SDK defensivo precisa de Pydantic, e o SDK de trajetória não tem dependências externas de runtime.

Abra `results/local-pilot-demo/index.html`. Duas ações sintéticas são executadas e uma tentativa fora da política é bloqueada pelo hospedeiro. O agente é roteirizado, sem LLM. Para repetir, escolha outro diretório: o comando recusa sobrescrita.

Os wheels permitem instalar os SDKs fora deste checkout. A demo é um exemplo do repositório e usa seu servidor MCP sintético; não faz parte dos wheels nem instala um adapter de produção.

## Validação independente

Instale `pytest` no ambiente de desenvolvimento e execute `python -m pytest tests/defense tests/trajectory tests/audit -q`. Verifique os artefatos com `python scripts/verify_sdk_release.py --output .review-build/defense-0.2.0 --rebuild-sdist` e o equivalente para trajetória. CI cobre uma matriz proposta Windows/Linux e Python3.10–3.12; não considere uma plataforma validada até o job correspondente passar.

## Evidência congelada no Windows

`.gitattributes` desativa transformação de finais de linha nos arquivos do dataset congelado. Se um checkout anterior transformou esses arquivos, `python scripts/verify_frozen_checkout.py --restore-exact-git-bytes` verifica o hash de cada blob original contra o relatório congelado antes de restaurar esses bytes. Nenhum hash, rótulo ou valor de dataset é recalculado para aceitar conteúdo diferente.

## Próximo uso

Consulte [kit de piloto](docs/pilot/README.md), [contrato defensivo](README_DEFENSIVE_SDK.md) e [jornadas operacionais](README_TRAJECTORY_SDK.md). SDKs alpha, sem parceiro confirmado ou validação externa. Credenciais e dados reais não são necessários para a demo.
