# -*- coding: utf-8 -*-
"""Aviso 8 (vedados em RPNP): leitura, portão contra o item 24 e aviso por OMDS (dados FICTÍCIOS, sem pessoa)."""
import datetime as dt
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "motor"))
import gof_avisos as av  # noqa: E402
import gof_vedados_rpnp as vd  # noqa: E402

CAB = ('"UG Executora"\t\t"NE CCor"\t"NE - Dia Emissão"\t"Conta Contábil"\t\t"622920101"\t"622920102"\t"622920103"\t"622920104"\n'
       ' \t\t \t \t"Natureza Despesa Detalhada"\t\t"Movim."\t"Movim."\t"Movim."\t"Movim."\n')
L = [
    ("160336", "160336000012026NE000010", "33901514", "1.000,00", "", "", ""),
    ("160336", "160336000012026NE000010", "33901514", "(400,00)", "0,00", "0,00", "400,00"),
    ("160336", "160336000012026NE000011", "33903030", "5.000,00", "", "", ""),
    ("160336", "160336000012026NE000012", "33909318", "250,50", "", "", ""),
    ("167336", "167336000012026NE000001", "33903996", "80,00", "", "", ""),
]


def csv_(linhas=L, extra_col=False):
    t = "Título\n" + CAB
    if extra_col:
        t = t.replace('"NE CCor"\t', '"NE CCor"\t"NE CCor - Favorecido"\t')
    for ug, ne, nd, a, b, c, d in linhas:
        t += '"%s"\t"X"\t"%s"\t"01/01/2026"\t"%s"\t"Y"\t"%s"\t"%s"\t"%s"\t"%s"\n' % (ug, ne, nd, a, b, c, d)
    t += '"160336"\t"X"\t"Total"\t""\t""\t\t"5.850,50"\t"0,00"\t"0,00"\t"400,00"\n'
    return t.encode("utf-16")


def regua(a160=5850.50, a167=80.0, data="2026-11-25"):
    return {"data_dado": data, "por_omds": {"DF": {"por_ug": {"160336": {"a_liquidar": a160}, "167336": {"a_liquidar": a167}}}}}


def test_calcula_e_agrega_sem_ne():
    r = vd.calcular(csv_(), regua(), "2026-11-25")
    assert r["n_ne"] == 3 and r["total"] == 930.5
    u = {x["ug"]: x for x in r["por_ug"]}
    assert u["160336"]["por_tipo"] == {"diárias": {"n_ne": 1, "valor": 600.0}, "ajuda de custo": {"n_ne": 1, "valor": 250.5}}
    assert u["167336"]["por_tipo"]["suprimento de fundos"]["valor"] == 80.0
    assert u["160336"]["ne"][0] == {"ne": "160336000012026NE000010", "tipo": "diárias", "valor": 600.0}  # NE sem pessoa


def test_portao_item24_e_data():
    with pytest.raises(ValueError, match="P-VD-1"):
        vd.calcular(csv_(), regua(a160=5850.49), "2026-11-25")
    with pytest.raises(ValueError, match="P-VD-1"):
        vd.calcular(csv_(), regua(data="2026-11-24"), "2026-11-25")


def test_recusa_favorecido():
    with pytest.raises(ValueError, match="P-VD-2"):
        vd.calcular(csv_(extra_col=True), regua(), "2026-11-25")


def test_aviso8_cor_e_prazo():
    ved = vd.calcular(csv_(), regua(), "2026-11-25")
    a = av.montar(dt.date(2026, 11, 26), 2026, vedados=ved)["por_omds"]["DF"]
    t = [x for x in a if "a liquidar" in x["titulo"] and "NE de" in x["titulo"]]
    assert len(t) == 2 and all(x["cor"] == "orange" for x in t)
    assert av.montar(dt.date(2026, 12, 24), 2026, vedados=ved)["por_omds"]["DF"][0]["cor"] == "red"
    assert av.montar(dt.date(2026, 12, 31), 2026, vedados=ved)["por_omds"] == {}


def test_detalhe_clicavel_lista_as_ne():
    ved = vd.calcular(csv_(), regua(), "2026-11-25")
    liq = {"por_omds": {"DF": {"por_ug": {"160336": {"a_liquidar": 300.0, "mais60_valor": 250.0, "mais60_ne": 1}}}},
           "por_ne": [{"ne": "160336000012026NE000020", "ug": "160336", "omds": "DF", "dias": 90, "favorecido": "EMPRESA X",
                       "a_liquidar": 250.0},
                      {"ne": "160336000012026NE000021", "ug": "160336", "omds": "DF", "dias": 10, "favorecido": "EMPRESA Y",
                       "a_liquidar": 50.0}]}
    a = av.montar(dt.date(2026, 11, 26), 2026, liquidacao=liq, vedados=ved)["por_omds"]["DF"]
    m60 = next(x for x in a if "60 dias" in x["titulo"])
    assert [i["ne"] for i in m60["itens"]] == ["160336000012026NE000020"] and m60["n_itens"] == 1
    emp = next(x for x in a if x["titulo"].startswith("Empenhos"))
    assert emp["n_itens"] == 2 and emp["itens"][0]["valor"] == 250.0
    ved_av = next(x for x in a if x["ug"] == "160336" and "NE de" in x["titulo"])
    assert {i["natureza"] for i in ved_av["itens"]} == {"diárias", "ajuda de custo"}
    assert all("_det" not in x for x in a)
