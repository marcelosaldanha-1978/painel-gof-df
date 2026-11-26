# -*- coding: utf-8 -*-
"""
gof_vedados_rpnp.py (v1.0, 26nov2026) — EMPENHOS DO EXERCÍCIO A LIQUIDAR QUE NÃO PODEM IR PARA RESTOS A PAGAR
(bloco `vedados_rpnp`; aviso 8 do encerramento, decisão do usuário de 26/11/2026, opção B).

Regra: diárias, ajuda de custo, indenização de transporte, ressarcimento de passagens e suprimento de fundos não se
inscrevem em RPNP: liquidar (e pagar) no exercício ou anular (Portaria SEF/C Ex nº 399/2026, Diretriz 6.d.3; Caderno
SEF de encerramento). Naturezas (8 dígitos): 339014* e 339015* (diárias), 33909314, 33909318, 33909319, subitem 96.

Entrada (assinatura do TG copiada pela ponte, SEM a coluna do favorecido):
  <entrega>_a_liquidar_natureza.csv  «<prefixo>A liquidar por NE e natureza detalhada 2026 (v1.0…)»: por UG, NE e
                                     natureza detalhada, contas 622920101..104 (a liquidar, em liquidação, a pagar, pago)
Saída: `dados/encerramento/vedados_rpnp.json`, por UG/OMDS e tipo, com a lista das NE para o detalhe do aviso
(número da NE, tipo e saldo; nenhuma pessoa).

Portões (a montagem não escreve se falharem; segue o arquivo anterior):
  P-VD-1  Σ (622920101 + 622920102) por UG = a_liquidar (item 24) da régua, mesma data do dado, ao centavo.
  P-VD-2  arquivo com coluna de favorecido é recusado (a ponte corta pelo nome do cabeçalho).
  (leitura) a linha «Total» que o TG põe por UG não é somada.
Medido em 26/11/2026 (exportação manual da v0.1): 6 UG = item 24 ao centavo; 69 NE vedadas, R$ 106.782,31.
"""
import collections
import datetime as dt
import io
import re
import sys as _sys
import zipfile
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent))

import gof_config as cfg  # noqa: E402
from gof_regua_tg import linhas  # noqa: E402
from gof_rp_por_ano import RE_PESSOA, num  # noqa: E402

RE_CONTA = re.compile(r"^6229201\d\d$")
RE_NE = re.compile(r"^\d{11}20\d\dNE\d{6}$")
RE_ND = re.compile(r"^\d{8}$")
TOL = 0.005

TIPOS = (  # (rótulo, teste); a primeira que casar vale
    ("diárias", lambda nd: nd.startswith(("339014", "339015"))),
    ("ajuda de custo", lambda nd: nd == "33909318"),
    ("indenização de transporte", lambda nd: nd == "33909319"),
    ("ressarcimento de passagens", lambda nd: nd == "33909314"),
    ("suprimento de fundos", lambda nd: nd[-2:] == "96"),
)


def tipo(nd):
    return next((t for t, f in TIPOS if f(nd)), None)


def ler(b, permitir_favorecido=False):
    """-> lista de (ug, ne, nd, a_liquidar) com a_liquidar = 101 + 102. Falha fechada se o cabeçalho não fecha."""
    ls = linhas(b)
    h = next((i for i, r in enumerate(ls) if sum(1 for c in r if RE_CONTA.match(c)) >= 2), None)
    if h is None:
        raise ValueError("cabeçalho com as contas 6229201xx não encontrado")
    cab = ls[h]
    if not permitir_favorecido and any(RE_PESSOA.search(c) for r in ls[h:h + 3] for c in r):
        raise ValueError("portão P-VD-2: arquivo com coluna de pessoa (a ponte tem de cortar o favorecido)")
    col = {c: j for j, c in enumerate(cab) if RE_CONTA.match(c)}
    if "622920101" not in col:
        raise ValueError("conta 622920101 ausente do cabeçalho")
    out = []
    for r in ls[h + 1:]:
        ne = next((c for c in r[:6] if RE_NE.match(c)), None)
        if not ne:
            continue  # linha «Total», subtítulos e linhas de continuação sem NE
        j = r.index(ne)
        nd = next((c for c in r[j + 1:col["622920101"]] if RE_ND.match(c)), None)
        if not nd:
            raise ValueError("NE %s sem natureza detalhada de 8 dígitos" % ne)
        a = sum(num(r[col[k]]) if col.get(k) is not None and col[k] < len(r) and r[col[k]] else 0.0
                for k in ("622920101", "622920102"))
        out.append((r[0] if re.fullmatch(r"\d{6}", r[0] or "") else ne[:6], ne, nd, a))
    if not out:
        raise ValueError("nenhuma linha de NE lida")
    return out


def omds_de(regua):
    return {ug: o for o, r in ((regua or {}).get("por_omds") or {}).items() for ug in (r.get("por_ug") or {})}


def calcular(b, regua, data_dado, permitir_favorecido=False):
    reg = ler(b, permitir_favorecido)
    if (regua or {}).get("data_dado") != data_dado:
        raise ValueError("portão P-VD-1: régua de %s, arquivo de %s" % ((regua or {}).get("data_dado"), data_dado))
    om = omds_de(regua)
    soma = collections.defaultdict(float)
    por_ne = collections.defaultdict(float)  # (ug, ne, tipo)
    for ug, ne, nd, a in reg:
        soma[ug] += a
        t = tipo(nd)
        if t:
            por_ne[(ug, ne, t)] += a
    div = []
    for r in regua["por_omds"].values():
        for ug, x in (r.get("por_ug") or {}).items():
            d = round(soma.get(ug, 0.0) - (x.get("a_liquidar") or 0), 2)
            if abs(d) > TOL:
                div.append({"ug": ug, "csv": round(soma.get(ug, 0.0), 2), "item24": x.get("a_liquidar"), "dif": d})
    fora = sorted(set(soma) - set(om))
    if div or fora:
        raise ValueError("portão P-VD-1: Σ(101+102) por UG ≠ item 24 da régua: %s %s" % (div, fora and "UG fora: %s" % fora))
    agg = {}
    for (ug, _ne, t), v in por_ne.items():
        if v <= TOL:
            continue
        x = agg.setdefault(ug, {"ug": ug, "omds": om.get(ug), "n_ne": 0, "valor": 0.0, "por_tipo": {}, "ne": []})
        x["ne"].append({"ne": _ne, "tipo": t, "valor": round(v, 2)})
        x["n_ne"] += 1
        x["valor"] += v
        pt = x["por_tipo"].setdefault(t, {"n_ne": 0, "valor": 0.0})
        pt["n_ne"] += 1
        pt["valor"] += v
    por_ug = sorted(agg.values(), key=lambda x: x["ug"])
    for x in por_ug:
        x["valor"] = round(x["valor"], 2)
        for pt in x["por_tipo"].values():
            pt["valor"] = round(pt["valor"], 2)
    return {"data_dado": data_dado, "por_ug": por_ug, "n_ne": sum(x["n_ne"] for x in por_ug),
            "total": round(sum(x["valor"] for x in por_ug), 2),
            "conferencia": "Σ (622920101 + 622920102) por UG = item 24 da régua, mesma data, ao centavo",
            "regra": "Diretriz 6.d.3 da Portaria SEF/C Ex nº 399/2026: vedada a inscrição em RPNP; liquidar ou anular"}


# ---------------------------------------------------------------- passo da montagem (nuvem)
RE_ARQ = re.compile(r"^(\d{4}-\d{2}-\d{2})_a_liquidar_natureza\.(csv|zip)$")


def escolher(nomes):
    ds = sorted(m.group(1) for m in map(RE_ARQ.match, nomes) if m)
    return ds[-1] if ds else None


def main(argv=None):
    import argparse
    import json

    ap = argparse.ArgumentParser(description="bloco vedados_rpnp: diárias, ajuda de custo e suprimento a liquidar")
    ap.add_argument("--regua", default="../dados/encerramento/regua.json")
    ap.add_argument("--saida", default="../dados/encerramento/vedados_rpnp.json")
    ap.add_argument("--local", default=None, help="CSV local (conferência; aceita a coluna do favorecido; não grava)")
    ap.add_argument("--data-dado", default=None, help="com --local: AAAA-MM-DD do dado (padrão: o da régua)")
    o = ap.parse_args(argv)
    if not cfg.bloco_ligado("vedados_rpnp"):
        print("VEDADOS_RPNP: bloco desligado no config; nada a fazer")
        return 0
    saida, regua_p = _Path(o.saida), _Path(o.regua)
    try:
        ant = json.loads(saida.read_text(encoding="utf-8")) if saida.exists() else {}
    except (OSError, ValueError):
        ant = {}
    try:
        regua = json.loads(regua_p.read_text(encoding="utf-8")) if regua_p.exists() else {}
        if o.local:
            r = calcular(_Path(o.local).read_bytes(), regua, o.data_dado or regua.get("data_dado"), True)
            print(json.dumps(r, ensure_ascii=False, indent=1))
            return 0
        import gof_google
        import gof_ponte_tg as pt
        tok = gof_google.token()
        arqs = pt.listar_pasta(tok)
        entrega = escolher(arqs)
        if not entrega:
            print("VEDADOS_RPNP: nenhum arquivo a_liquidar_natureza na pasta; vigente (%s) mantido" % ant.get("data_dado"))
            return 2
        data_dado = pt.dia_util_anterior(dt.date.fromisoformat(entrega)).isoformat()
        if data_dado <= (ant.get("data_dado") or ""):
            print("VEDADOS_RPNP: arquivo de %s não é mais novo que o vigente; nada a fazer" % entrega)
            return 0
        nome = next(n for n in arqs if RE_ARQ.match(n) and n.startswith(entrega + "_"))
        b = pt._get("https://www.googleapis.com/drive/v3/files/%s?alt=media" % arqs[nome], tok)
        if nome.endswith(".zip"):
            z = zipfile.ZipFile(io.BytesIO(b))
            b = z.read(z.namelist()[0])
        r = calcular(b, regua, data_dado)
    except (OSError, ValueError, RuntimeError, KeyError, StopIteration) as e:
        print("VEDADOS_RPNP: falhou (%s: %s); vigente (%s) mantido" % (type(e).__name__, e, ant.get("data_dado")))
        return 2
    r["fonte"] = "TG, assinatura «%sA liquidar por NE e natureza detalhada» (%s, via ponte)" % (
        (cfg.carregar().get("assinaturas_tg") or {}).get("prefixo_assunto", ""), nome)
    saida.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print("VEDADOS_RPNP: dados até %s — %d NE vedadas, R$ %.2f" % (r["data_dado"], r["n_ne"], r["total"]))
    return 0


if __name__ == "__main__":
    _sys.exit(main())
