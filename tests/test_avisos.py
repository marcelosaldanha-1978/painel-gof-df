# -*- coding: utf-8 -*-
"""Avisos do encerramento (gof_avisos.py, 26/11/2026): aparecem, mudam de cor com a data e somem quando resolvidos."""
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "motor"))
import gof_avisos as A  # noqa: E402

D = dt.date
REC = D(2026, 11, 26)


def rp(*linhas):
    return {"por_ug": [{"omds": o, "ug": u, "ano": a, "a_liquidar": al, "em_liquidacao": 0.0, "bloqueado": b} for o, u, a, al, b in linhas]}


def tit(r, o):
    return [(a["ug"], a["cor"], a["titulo"]) for a in r["por_omds"].get(o, [])]


def test_rpnp_2023_vermelho_ate_30_12_e_some_quando_zera():
    r = A.montar(D(2026, 11, 26), 2026, rp=rp(("AGR", "167285", 2023, 438121.61, 0.0)))
    a = r["por_omds"]["AGR"][0]
    assert (a["cor"], a["valor"]) == ("red", 438121.61) and "30/12" in a["texto"] and "29/12" in a["texto"]
    assert "UGR" in a["texto"] and "§ 7º" in a["fundamento"]
    assert A.montar(D(2026, 11, 27), 2026, rp=rp(("AGR", "167285", 2023, 0.0, 0.0)))["n"] == 0


def test_rpnp_2024_bloqueado_laranja_ate_23_12_depois_vermelho():
    x = rp(("DF", "160336", 2024, 0.0, 5000.0))
    assert tit(A.montar(D(2026, 12, 23), 2026, rp=x), "DF")[0][1] == "orange"
    assert tit(A.montar(D(2026, 12, 24), 2026, rp=x), "DF")[0][1] == "red"


def test_rpnp_2025_informativo_azul():
    assert tit(A.montar(D(2026, 11, 26), 2026, rp=rp(("DF", "160336", 2025, 10.0, 0.0))), "DF") == [
        ("160336", "blue", "RPNP de 2025 a liquidar")]


def test_indicacao_muda_de_cor_com_a_data():
    lq = {"por_omds": {"DF": {"por_ug": {"160336": {"a_liquidar": 100.0}}}}}
    cores = [tit(A.montar(D(2026, m, d), 2026, liquidacao=lq), "DF")[0][1] for m, d in ((11, 30), (12, 1), (12, 23), (12, 24))]
    assert cores == ["blue", "orange", "orange", "gray"]
    assert A.montar(D(2026, 12, 31), 2026, liquidacao=lq)["n"] == 0


def test_mais_60_dias_e_residual():
    lq = {"por_omds": {"AGR": {"por_ug": {"160285": {"a_liquidar": 0.0, "mais60_valor": 900.0, "mais60_ne": 3}}}},
          "por_ne": [{"omds": "AGR", "ug": "160285", "ne": "160285x", "a_liquidar": 12.5},
                     {"omds": "AGR", "ug": "160285", "ne": "160285y", "a_liquidar": 150.0}]}
    r = A.montar(D(2026, 11, 26), 2026, liquidacao=lq)
    assert tit(r, "AGR") == [("160285", "orange", "3 NE sem liquidação há mais de 60 dias"),
                             ("160285", "gray", "1 NE com saldo residual")]
    assert r["por_omds"]["AGR"][1]["valor"] == 12.5


def test_credito_com_prazo_e_liquidado_a_pagar():
    rg = {"por_omds": {"AGSP": {"por_ug": {"160529": {"em_tela": 50.0, "estado": {"cod": "NO_PRAZO"},
                                                     "liquidado_a_pagar": 70.0, "rpnp_liquidado_a_pagar": 30.0}}}}}
    r = A.montar(D(2026, 12, 2), 2026, regua=rg, data_recolhimento=REC)
    assert tit(r, "AGSP") == [("160529", "orange", "Crédito em tela com prazo da NC"), ("160529", "blue", "Liquidado e não pago")]
    assert r["por_omds"]["AGSP"][1]["valor"] == 100.0
    assert tit(A.montar(D(2026, 12, 5), 2026, regua=rg, data_recolhimento=REC), "AGSP") == [
        ("160529", "blue", "Liquidado e não pago")]
    # no dia do recolhimento o crédito é tratado pela etiqueta, não pelo aviso
    assert "Crédito em tela com prazo da NC" not in str(A.montar(REC, 2026, regua=rg, data_recolhimento=REC))


def test_datas_do_calendario_prevalecem():
    cal = {"datas_avisos": {"indicacao_fim": "2026-12-22"}}
    lq = {"por_omds": {"DF": {"por_ug": {"160336": {"a_liquidar": 1.0}}}}}
    assert tit(A.montar(D(2026, 12, 23), 2026, liquidacao=lq, calendario=cal), "DF")[0][1] == "gray"
