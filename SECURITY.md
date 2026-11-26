# Segurança

- **Segredos (2, só de leitura):** `GOOGLE_SA_JSON` (conta de serviço que lê a pasta privada da ponte) e
  `PORTAL_TRANSPARENCIA_API_KEY`. Nenhuma credencial em arquivo do repositório.
- **Dado pessoal:** CPF de pessoa física é mascarado na ponte (Apps Script) e de novo no motor; o verificador de saída
  reprova a publicação se achar CPF inteiro.
- **Workflows:** actions fixadas por SHA, `contents: read` por padrão, `persist-credentials: false`.
- **Isolamento:** esta cadeia não lê nem grava nada do painel GOF-BaApLog (pasta, conta de serviço, repositório e
  assuntos de e-mail próprios; a ponte recusa rodar se algum deles for o da BaApLog).

Achou um problema? Abra uma issue sem dados sensíveis.
