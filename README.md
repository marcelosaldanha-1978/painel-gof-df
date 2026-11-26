# Painel GOF-DF

Painel de gestão orçamentária e financeira da **Diretoria de Fabricação** (Exército Brasileiro): crédito, empenho, liquidação,
restos a pagar e contratos da DF (UG 160336/167336), do AGR (160285/167285) e do AGSP (160529/167529), direto do Tesouro
Gerencial, todo dia útil, na nuvem e sem computador ligado.

**Página:** https://marcelosaldanha-1978.github.io/painel-gof-df/

## Como funciona

1. O Tesouro Gerencial envia por e-mail, de madrugada, as assinaturas `PAINEL-DF-CONF-…` (CSV).
2. Uma ponte no Google Apps Script («Ponte TG DF», 06h e 11h) copia os anexos para uma pasta privada do Drive
   (`PONTE_TG_SEM_PESSOA_DF`), com CPF de pessoa física mascarado, lida só por uma conta de serviço de leitura.
3. O workflow **Montagem e publicação** lê a pasta, confere os números ao centavo (portões), monta a página e publica no
   GitHub Pages. Se um portão reprovar, nada é publicado e fica a página anterior.
4. O workflow **Vigia** abre uma issue se a montagem não rodar ou se o dado parar de andar.

## Código

Cópia do código do [painel GOF-BaApLog](https://github.com/marcelosaldanha-1978/painel-gof-baaplog) (mesmo motor, configurado
por `config/om.json`). O que muda de uma OM para outra está só no config; cadeias, pastas, contas de serviço e segredos são
separados. Favorecido: nome e CNPJ; CPF de pessoa física sempre mascarado (`***.ddd.ddd-**`).

## Conferir localmente

```
pip install -r requirements.txt
python motor/verificar_config.py
python -m pytest tests -q
```
