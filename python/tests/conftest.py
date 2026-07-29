"""Тесты не должны зависеть от настроек машины, на которой их запускают.

httpx по умолчанию читает прокси из окружения, а на Windows — ещё и из реестра.
Если у разработчика включён системный прокси, конструктор httpx.Client падает
или пытается ходить через него, и падают тесты, которые вообще не про сеть.
`no_proxy=*` заставляет httpx игнорировать любой прокси, откуда бы он ни взялся.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _no_ambient_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("no_proxy", "*")
    monkeypatch.setenv("NO_PROXY", "*")
