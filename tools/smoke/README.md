# Smoke scripts

Headless smoke scripts that boot a full Game and exercise click->effect chains. Run individually with `source source_me.sh && python3 tools/smoke/<script>.py`. They are not part of the pytest suite by design (per [docs/PYTHON_STYLE.md](../../docs/PYTHON_STYLE.md), integration scripts with multi-step setup belong here, not in tests/).
