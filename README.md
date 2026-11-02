# Data Engine Tool

Aplicativo Python com Streamlit para criar processos reutilizáveis de dados. No modo local, você informa caminhos e executa no seu computador. No modo web, envia os arquivos pelo navegador e os blocos rodam no servidor.

## Abrir

1. Instale Python 3.10 ou mais recente.
2. Dê dois cliques em `Abrir_Data_Engine.bat`. Na primeira abertura, o inicializador instala o Streamlit e os leitores de arquivo incluídos se ainda estiverem faltando.
3. O aplicativo abre em `http://127.0.0.1:8501` e cria um projeto de exemplo CSV.

## Publicação Streamlit com upload

Nas configurações do app hospedado, defina a variável `DATA_ENGINE_MODE=web` (no Streamlit Community Cloud, adicione `DATA_ENGINE_MODE = "web"` em **Settings → Secrets**). Esse modo remove os campos de caminhos do computador e a pasta de destino local; os arquivos são enviados pelo navegador e os resultados são baixados pela própria página. Os códigos de entrada continuam recebendo `files`, uma lista de objetos `Path` numa pasta temporária do servidor.

Esse modo permite validar o fluxo de upload e execução na web, mas ainda não oferece persistência compartilhada confiável: configurações de projetos e histórico ficam no disco da aplicação; os uploads são mantidos em memória e copiados para uma pasta temporária somente durante a execução. No Streamlit Community Cloud, arquivos criados durante o uso não têm persistência garantida entre sessões. Para compartilhar projetos de forma durável entre colaboradores, conecte um banco de dados persistente para configuração/histórico e armazenamento de objetos para arquivos. Essas integrações não estão implementadas nesta versão.

**Não precisa instalar Docker.** Esta primeira versão usa o Python local para a interface e para executar os blocos. Todos os códigos usam as bibliotecas instaladas nesse mesmo ambiente. Um ambiente virtual separado por projeto pode ser adicionado depois caso apareçam dependências incompatíveis.

## Como o código participa do processamento

O código é salvo dentro do projeto. Ao executar, o motor localiza os arquivos e inicia um processo Python filho para cada bloco. As entradas marcadas rodam na ordem configurada. Depois, o processamento geral (se preenchido) e a saída recebem somente os resultados dessas entradas.

### Código de entrada

O motor entrega `files`, uma lista de objetos `pathlib.Path` para os arquivos encontrados. O código lê os arquivos e define `result` com dados que possam ser convertidos em JSON.

```python
import csv

result = []
for file_path in files:
    with file_path.open(encoding="utf-8-sig", newline="") as source:
        result.extend(dict(row) for row in csv.DictReader(source))
```

### Processamento geral opcional

O bloco recebe `inputs`, um dicionário que associa o nome de cada entrada ao resultado correspondente. Defina `result` com a consolidação. Entradas desmarcadas não aparecem nesse dicionário. Para fontes diferentes que usam o mesmo processamento e saída, cada entrada deve preparar o resultado em um formato comum.

```python
all_rows = []
for entry_name, rows in inputs.items():
    for row in rows:
        row["fonte"] = entry_name
        all_rows.append(row)
result = all_rows
```

### Saída

O bloco recebe `data` e `output_dir`, um objeto `Path`. Crie os arquivos finais dentro dessa pasta.

```python
import csv

records = data["Movimentos"]
columns = list(records[0]) if records else []
with (output_dir / "resultado.csv").open("w", encoding="utf-8-sig", newline="") as destination:
    writer = csv.DictWriter(destination, fieldnames=columns)
    writer.writeheader()
    writer.writerows(records)
```

De um a quatro arquivos gerados aparecem como downloads individuais. A partir de cinco, o Data Engine oferece um ZIP. No modo local, você também pode preencher uma pasta para copiar os resultados; no modo web, os arquivos são baixados pelo navegador.

No modo local, arquivos escolhidos pelo seletor de upload são copiados automaticamente para a entrada correspondente. No modo web, os arquivos selecionados são usados somente na execução atual e não são guardados no projeto.

## Selecionar entradas

Marque “Incluir esta entrada na próxima execução” nos cartões desejados. Entradas desmarcadas não precisam ter arquivos para aquela rodada. Os leitores das entradas marcadas executam e seus resultados passam pelo processamento e pela saída configurados. Não existe opção que execute somente os leitores e ignore as etapas seguintes.

## Sobre e manuais

A aba “Sobre e manuais” explica o fluxo e permite baixar o Manual para IA em PDF ou Markdown. Os arquivos são lidos da pasta `documentacao/`, que precisa acompanhar `app.py` quando o aplicativo for empacotado.

Na web, os códigos Python rodam com as permissões do processo no servidor. Mesmo para um grupo de colaboradores confiáveis, um erro no código pode acessar dados ou recursos disponíveis à aplicação. Restrinja o acesso à equipe e planeje armazenamento persistente e controles por usuário antes de tratar esta versão como serviço colaborativo de produção.

## Persistência e repetição

Cada projeto salva códigos e configuração em `data/projects/<projeto>/project.json`. As execuções e seus resultados ficam na pasta `runs/`. No modo local, novos arquivos podem ser adicionados aos caminhos configurados. No modo web, envie os arquivos no navegador para a entrada correspondente. Esta versão roda sob demanda; não monitora pastas nem agenda execuções automaticamente.

## Código Python

Cada bloco roda em processo Python separado para que erros e interrupções não encerrem diretamente a interface. No modo local, o código recebe as permissões da sua conta Windows; no modo web, recebe as permissões do servidor. Execute somente código que você entende ou revisou. O processo filho melhora a estabilidade; ele não é um sandbox de segurança.

## Estrutura

- `app.py`: interface Streamlit local/web.
- `engine.py`: projetos, localização de fontes, persistência e orquestração.
- `runner.py`: execução de cada bloco em processo Python separado.
- `data/projects/`: configurações, histórico e resultados.
- `requirements.txt`: dependências da interface e leitores comuns.
