# -*- coding: utf-8 -*-
"""
gof_avisos.py (v1.0, 26nov2026) — AVISOS DO ENCERRAMENTO por OMDS e UG (decisão do usuário de 26/11/2026, opção B).

Recalculado em toda montagem a partir dos dados do dia: o aviso some quando a situação se resolve, entra quando aparece
e muda de cor conforme a data da Portaria se aproxima. Só agregado por UG (nenhuma NE, nenhuma pessoa na saída).

Fontes da regra (proposta auditada às cegas em 26/11, /mnt/project-files/df-avisos/avisos_encerramento_proposta_v1.md):
  Portaria SEF/C Ex nº 399/2026 (Diretriz «Dtz» e Calendário «ev.»); Decreto 93.872/1986, art. 68 (texto vigente no
  Planalto em 24/11/2026). As datas vêm de `datas_avisos` do calendário do exercício (config/calendario/...json).

Entradas (todas opcionais; o aviso que depende de uma entrada ausente simplesmente não sai):
  regua       dados/encerramento/regua.json (com `estado` de gof_estado_tela; itens 26 e 45 desde a v1.1 da régua)
  liquidacao  dados/liquidacao/ultimo.json (a liquidar por UG, +60 dias; `por_ne` só quando o config libera)
  rp          dados/encerramento/rp_por_ano.json (RPNP por UG e ano de inscrição)
  vedados     dados/encerramento/vedados_rpnp.json (diárias, ajuda de custo e suprimento a liquidar; v1.1, aviso 8)
"""
import datetime as dt

NIVEL = {"red": 0, "orange": 1, "amber": 2, "blue": 3, "gray": 4}
RESIDUAL = 100.0  # saldo de NE abaixo disso conta como residual (Dtz 6.d.2; limite proposto em 26/11)
TOL = 0.005

PADRAO = {  # Portaria 399/2026; o calendário do exercício pode trocar cada data
    "indicacao_inicio": "12-01", "indicacao_fim": "12-23", "desbloqueio_rpnp": "12-23",
    "liquidar_para_pagar": "12-29", "prazo_final": "12-30", "empenho_remanejado": "12-03",
    "empenho_autorizado": "12-04"}


def datas(calendario, exercicio):
    d = {k: "%d-%s" % (exercicio, v) for k, v in PADRAO.items()}
    d.update((calendario or {}).get("datas_avisos") or {})
    return {k: dt.date.fromisoformat(v) for k, v in d.items()}


def _br(d):
    return d.strftime("%d/%m")


def _av(ug, nivel, titulo, texto, valor, fund):
    return {"ug": ug, "cor": nivel, "titulo": titulo, "texto": texto, "valor": round(valor, 2), "fundamento": fund}


def montar(hoje, exercicio, regua=None, liquidacao=None, rp=None, calendario=None, data_recolhimento=None,
           vedados=None):
    """-> {"por_omds": {omds: [aviso…]}, "n": total, "regra": texto}. Avisos ordenados por gravidade e UG."""
    D = datas(calendario, exercicio)
    por = {}

    def add(omds, a):
        por.setdefault(omds, []).append(a)

    # 1, 2 e 7 · restos a pagar por ano de inscrição
    for x in ((rp or {}).get("por_ug") or []) if not (rp or {}).get("ausente") else []:
        ano, ug, o = x["ano"], x["ug"], x["omds"]
        saldo = (x.get("a_liquidar") or 0) + (x.get("em_liquidacao") or 0)
        bloq = x.get("bloqueado") or 0
        if ano <= exercicio - 3:
            if saldo > TOL:
                if hoje <= D["prazo_final"]:
                    add(o, _av(ug, "red", "RPNP de %d a liquidar" % ano,
                               "Liquidar até %s para pagar ainda em %d; prazo final %s. O que restar é cancelado em 31/12 "
                               "e a UGE justifica à UGR." % (_br(D["liquidar_para_pagar"]), exercicio, _br(D["prazo_final"])),
                               saldo, "Portaria 399, ev. 26 e 27; Dtz 6.b.1; Dec. 93.872, art. 68, § 7º"))
                else:
                    add(o, _av(ug, "red", "RPNP de %d com saldo depois do prazo" % ano,
                               "Conferir o cancelamento automático e a justificativa à UGR.", saldo,
                               "Dec. 93.872, art. 68, § 7º; Dtz 6.b.1"))
            if bloq > TOL:
                add(o, _av(ug, "orange", "RPNP de %d ainda bloqueado" % ano,
                           "O prazo de desbloqueio terminou em 31/12/%d. Conferir a situação com o CGCFEx." % (ano + 2),
                           bloq, "Dec. 93.872, art. 68, §§ 2º e 4º"))
        elif ano == exercicio - 2 and bloq > TOL:
            cor = "orange" if hoje <= D["desbloqueio_rpnp"] else "red"
            add(o, _av(ug, cor, "RPNP de %d bloqueado" % ano,
                       ("Desbloquear até %s o que teve execução iniciada até 30/06/%d; sem desbloqueio, não se liquida."
                        % (_br(D["desbloqueio_rpnp"]), exercicio)) if cor == "orange" else
                       "Prazo de desbloqueio da Portaria encerrado. Conferir com o CGCFEx.",
                       bloq, "Portaria 399, ev. 19; Dtz 6.b.2; Dec. 93.872, art. 68, §§ 4º e 5º"))
        if ano == exercicio - 2 and saldo > TOL:
            add(o, _av(ug, "blue", "RPNP de %d a liquidar" % ano,
                       "Priorizar a liquidação até %s. Se não for liquidado, é cancelado em 31/12/%d."
                       % (_br(D["prazo_final"]), exercicio + 1), saldo, "Dtz 6.b.2; Dec. 93.872, art. 68, § 7º"))
        elif ano == exercicio - 1 and saldo > TOL:
            add(o, _av(ug, "blue", "RPNP de %d a liquidar" % ano,
                       "Será reinscrito em 31/12/%d e bloqueado em 30/06/%d se não for liquidado. Ultimar a liquidação."
                       % (exercicio, exercicio + 1), saldo, "Dtz 6.b.3; Dec. 93.872, art. 68, § 2º"))

    # 3 · NE do exercício a liquidar: indicação para RPNP · 6 · mais de 60 dias
    for o, r in ((liquidacao or {}).get("por_omds") or {}).items():
        for ug, x in (r.get("por_ug") or {}).items():
            al = x.get("a_liquidar") or 0
            if al > TOL and hoje <= D["prazo_final"]:
                if hoje < D["indicacao_inicio"]:
                    cor, txt = "blue", ("Indicar no SIAFI, de %s a %s, as NE que vão para restos a pagar; a não indicada "
                                        "é anulada no fechamento." % (_br(D["indicacao_inicio"]), _br(D["indicacao_fim"])))
                elif hoje <= D["indicacao_fim"]:
                    cor, txt = "orange", ("Indicar no SIAFI até %s as NE que vão para restos a pagar; a não indicada é "
                                          "anulada no fechamento." % _br(D["indicacao_fim"]))
                else:
                    cor, txt = "gray", ("Indicação encerrada em %s. A NE não indicada que restar é anulada até %s."
                                        % (_br(D["indicacao_fim"]), _br(D["prazo_final"])))
                add(o, _av(ug, cor, "Empenhos de %d a liquidar" % exercicio, txt, al,
                           "Portaria 399, ev. 9, 20 e 32; Dec. 93.872, art. 68, § 1º"))
            m60 = x.get("mais60_valor") or 0
            if m60 > TOL:
                nn = x.get("mais60_ne") or 0
                add(o, _av(ug, "orange", "%d NE sem liquidação há mais de 60 dias" % nn if nn != 1 else
                           "1 NE sem liquidação há mais de 60 dias",
                           "Avaliar novo fornecedor, devolução do crédito ou anulação, e se cabe inscrever em restos a pagar.",
                           m60, "Dtz 6.d.1 e 6.e.1"))

    # 5 · saldos residuais de NE (só quando a lista por NE existe)
    resid = {}
    for x in (liquidacao or {}).get("por_ne") or []:
        v = x.get("a_liquidar") or 0
        if TOL < v < RESIDUAL:
            k = (x.get("omds"), x.get("ug") or str(x.get("ne", ""))[:6])
            resid.setdefault(k, [0, 0.0])
            resid[k][0] += 1
            resid[k][1] += v
    for (o, ug), (nn, v) in resid.items():
        add(o, _av(ug, "gray", ("%d NE com saldo residual" % nn) if nn != 1 else "1 NE com saldo residual",
                   "Saldo abaixo de R$ 100 por NE: cancelar.", v, "Dtz 6.d.2"))

    # 4 · crédito em tela com prazo da NC · 3 · liquidado a pagar
    d_rec = data_recolhimento
    for o, r in ((regua or {}).get("por_omds") or {}).items():
        for ug, x in (r.get("por_ug") or {}).items():
            es = x.get("estado") or {}
            if es.get("cod") == "NO_PRAZO" and d_rec and hoje > d_rec and hoje <= D["empenho_autorizado"] \
                    and (x.get("em_tela") or 0) > TOL:
                add(o, _av(ug, "orange", "Crédito em tela com prazo da NC",
                           "Empenhar até %s (créditos remanejados) ou %s, se a UGR autorizou; sem empenho, recolher."
                           % (_br(D["empenho_remanejado"]), _br(D["empenho_autorizado"])),
                           x.get("em_tela") or 0, "Portaria 399, ev. 10 e 12"))
            ap = (x.get("liquidado_a_pagar") or 0) + (x.get("rpnp_liquidado_a_pagar") or 0)
            if ap > TOL and hoje <= D["prazo_final"]:
                cor = "orange" if hoje > D["indicacao_fim"] else "blue"
                add(o, _av(ug, cor, "Liquidado e não pago",
                           "Pagar ainda em %d: ordem bancária até 14h de %s (liquidação até %s)."
                           % (exercicio, _br(D["prazo_final"]), _br(D["liquidar_para_pagar"])),
                           ap, "Portaria 399, ev. 27 e 28; Dtz 4.c.1"))

    # 8 · diárias, ajuda de custo e suprimento a liquidar: não vão para restos a pagar (gof_vedados_rpnp)
    for x in ((vedados or {}).get("por_ug") or []) if not (vedados or {}).get("ausente") else []:
        if (x.get("valor") or 0) <= TOL or hoje > D["prazo_final"]:
            continue
        nn = x.get("n_ne") or 0
        ts = sorted(x.get("por_tipo") or {})
        tipos = ts[0] if len(ts) == 1 else ", ".join(ts[:-1]) + " e " + ts[-1]
        add(x.get("omds"), _av(x["ug"], "red" if hoje > D["indicacao_fim"] else "orange",
                               "%d NE de %s a liquidar" % (nn, tipos) if nn != 1 else "1 NE de %s a liquidar" % tipos,
                               "Não podem ir para restos a pagar: liquidar até %s para pagar ainda em %d, ou anular."
                               % (_br(D["liquidar_para_pagar"]), exercicio),
                               x["valor"], "Dtz 6.d.3; Portaria 399, ev. 27"))

    for o in por:
        por[o].sort(key=lambda a: (NIVEL.get(a["cor"], 9), a["ug"], -a["valor"]))
    return {"por_omds": por, "n": sum(len(v) for v in por.values()),
            "regra": "Avisos recalculados a cada publicação pela Portaria SEF/C Ex nº 399/2026 e pelo Dec. 93.872/1986, "
                     "art. 68; somem quando a situação se resolve."}
