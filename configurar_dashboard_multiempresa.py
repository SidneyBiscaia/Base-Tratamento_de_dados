"""Cria o projeto de teste multiempresa dentro do Data Engine instalado."""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import engine


PROJECT_NAME = "Dashboard Contábil Multiempresa"
PROJECT_ID = "dashboard-contabil-multiempresa-2026"
APP_DIR = Path(__file__).resolve().parent

BILLING_PATH = r"C:\Users\Usuario\Downloads\Planilhas do Dash\Faturamento\FATURAMENTO 08.2026.xlsx"
TAX_PATH = r"C:\Users\Usuario\Downloads\Planilhas do Dash\Tributos\Imposto por mes.xlsx"
SALES_PATH = r"C:\Users\Usuario\Downloads\Planilhas do Dash\Vendas\Vendas 08.2026.xlsx"
REFERENCE_PATH = r"C:\Users\Usuario\Downloads\Planilhas do Dash\Planilhas\008 - Nóbrega - Dash.xlsx"

BILLING_CODE = r'''import re
import openpyxl

def number(value):
    if isinstance(value, (int, float)):
        return float(value)
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip().replace("R$", "").replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None

result = []
for file_path in files:
    workbook = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    for index, row in enumerate(rows):
        first = str(row[0] if row else "")
        match = re.search(r"CNPJ\s*:\s*([0-9./-]+)", first, re.I)
        if not match:
            continue
        cnpj = re.sub(r"\D", "", match.group(1))
        company = None
        for back in range(index - 1, max(-1, index - 15), -1):
            prior_row = rows[back]
            candidate = str(prior_row[0] if prior_row else "").strip()
            if re.match(r"^\d{3,5}\s+", candidate):
                company = re.sub(r"^\d{3,5}\s+", "", candidate).strip()
                break
        total = None
        for forward in range(index + 1, min(len(rows), index + 100)):
            next_row = rows[forward]
            first_cell = str(next_row[0] if next_row else "").strip().upper()
            if first_cell == "TOTAL":
                total = rows[forward]
                break
            # The next CNPJ marks the next company if this report block has no total.
            if re.search(r"CNPJ\s*:", first_cell):
                break
        period_text = str(row[3] or "")
        dates = re.findall(r"\d{2}/\d{2}/\d{4}", period_text)
        period = dates[0][6:10] + "-" + dates[0][3:5] if dates else None
        result.append({
            "empresa": company or "Empresa sem nome",
            "cnpj": cnpj,
            "mes": period,
            "mercadorias": number(total[2]) if total else None,
            "servicos": number(total[3]) if total else None,
            "faturamento_relatorio": number(total[4]) if total else None,
            "arquivo": file_path.name,
        })
    workbook.close()
'''

TAX_CODE = r'''import openpyxl
from datetime import date, datetime
import re

def as_month(value):
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m")
    text = str(value or "").strip()
    match = re.search(r"(\d{4})-(\d{2})", text)
    if match:
        return match.group(1) + "-" + match.group(2)
    match = re.search(r"(\d{2})/(\d{4})", text)
    return match.group(2) + "-" + match.group(1) if match else None

result = []
for file_path in files:
    workbook = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
    sheet = workbook.active
    for row in sheet.iter_rows(min_row=2, values_only=True):
        company, cnpj, period, category, amount, count = (list(row) + [None] * 6)[:6]
        if not company:
            continue
        try:
            amount = float(amount) if amount is not None else None
        except (TypeError, ValueError):
            amount = None
        result.append({
            "empresa": str(company).strip(),
            "cnpj": "".join(ch for ch in str(cnpj or "") if ch.isdigit()),
            "mes": as_month(period),
            "categoria": str(category or "Sem categoria").strip(),
            "valor": amount,
            "quantidade_obrigacoes": int(count) if count is not None else None,
        })
    workbook.close()
'''

SALES_CODE = r'''import openpyxl
from datetime import date, datetime

result = []
for file_path in files:
    workbook = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
    sheet = workbook.active
    for row in sheet.iter_rows(min_row=2, values_only=True):
        values = list(row) + [None] * 15
        branch, company, launch, customer_id, customer, uf, document, kind, series, dt, nature, description, user, amount, extra = values[:15]
        if not company:
            continue
        if isinstance(dt, (date, datetime)):
            dt = dt.strftime("%Y-%m-%d")
        else:
            dt = str(dt or "").strip()
            try:
                dt = datetime.strptime(dt, "%d/%m/%Y").strftime("%Y-%m-%d")
            except ValueError:
                pass
        try:
            amount = float(amount) if amount is not None else 0.0
        except (TypeError, ValueError):
            amount = 0.0
        result.append({
            "filial": str(branch or ""), "empresa": str(company).strip(),
            "id_cliente": str(customer_id or ""), "cliente": str(customer or "Sem identificação"),
            "uf": str(uf or "").strip().upper(), "documento": str(document or ""),
            "especie": str(kind or ""), "serie": str(series or ""),
            "data": dt, "descricao": str(description or ""), "valor_contabil": amount,
        })
    workbook.close()
'''

PROCESS_CODE = r'''import re
import unicodedata
from collections import defaultdict

def key(value):
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"\b(matriz|filial|ltda|sa|s a|eireli|me|epp)\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", "", text)
    # One source file contains a second, text-corrupted spelling of Joaomed.
    if text.startswith("joomed"):
        text = "joaomed" + text[len("joomed"):]
    return text

billing = inputs["Faturamento"]
tax_rows = inputs["Impostos"]
sales_rows = inputs["Vendas"]

companies = {}
for row in billing:
    if not row.get("cnpj") or not row.get("mes"):
        continue
    item = dict(row)
    item["chave_empresa"] = key(row.get("empresa"))
    item["impostos"] = []
    item["vendas"] = []
    companies[(item["cnpj"], item["mes"])] = item

by_cnpj_month = {(item["cnpj"], item["mes"]): item for item in companies.values()}
for tax in tax_rows:
    target = by_cnpj_month.get((tax.get("cnpj"), tax.get("mes")))
    if target:
        target["impostos"].append(tax)

keys_by_company = {}
for item in companies.values():
    keys_by_company.setdefault(item["chave_empresa"], []).append(item)

unmatched_sales = set()
for sale in sales_rows:
    period = str(sale.get("data", ""))[:7]
    sale_key = key(sale.get("empresa"))
    target = None
    for item in companies.values():
        if item["mes"] != period:
            continue
        candidate = item["chave_empresa"]
        if candidate == sale_key:
            target = item
            break
    if target is None:
        candidates = [item for item in companies.values() if item["mes"] == period and (item["chave_empresa"].startswith(sale_key) or sale_key.startswith(item["chave_empresa"]))]
        if len(candidates) == 1:
            target = candidates[0]
    if target:
        target["vendas"].append(sale)
    else:
        unmatched_sales.add(str(sale.get("empresa")))

result = []
for item in companies.values():
    sales = item["vendas"]
    invoices = {(s["filial"], s["documento"], s["especie"], s["serie"]) for s in sales if s["documento"]}
    states = defaultdict(float)
    customers = defaultdict(float)
    for sale in sales:
        amount = sale.get("valor_contabil") or 0.0
        states[sale.get("uf") or "Sem UF"] += amount
        customers[sale.get("cliente") or "Sem identificação"] += amount
    item["vendas_total"] = sum((s.get("valor_contabil") or 0.0) for s in sales)
    item["notas_unicas"] = len(invoices)
    item["clientes_unicos"] = len({s.get("id_cliente") or s.get("cliente") for s in sales if s.get("id_cliente") or s.get("cliente")})
    item["vendas_por_uf"] = sorted([{"uf": k, "valor": v} for k, v in states.items()], key=lambda x: x["valor"], reverse=True)[:8]
    item["principais_clientes"] = sorted([{"cliente": k, "valor": v} for k, v in customers.items()], key=lambda x: x["valor"], reverse=True)[:5]
    item["impostos_total"] = sum((tax.get("valor") or 0.0) for tax in item["impostos"])
    item["categorias_impostos"] = sorted(item["impostos"], key=lambda x: x.get("valor") or 0.0, reverse=True)
    item["tem_vendas"] = bool(sales)
    item["tem_impostos"] = bool(item["impostos"])
    item["diferenca_faturamento_vendas"] = (item.get("faturamento_relatorio") or 0.0) - item["vendas_total"] if sales else None
    del item["vendas"]
    del item["impostos"]
    result.append(item)

result.sort(key=lambda x: (x["empresa"].casefold(), x["mes"]))
result = {"paineis": result, "vendas_sem_correspondencia": sorted(unmatched_sales), "fonte_referencia": "008 - Nóbrega - Dash.xlsx"}
'''

OUTPUT_CODE = r'''import csv
import html
import json
import re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

panels = data["paineis"]
if not panels:
    raise ValueError("Nenhum painel foi montado. Confira se faturamento, mês e empresas foram identificados.")

def money(value):
    if value is None:
        return "Sem dado"
    return "R$ " + f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def safe_name(value):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(value)).strip("_")[:70] or "empresa"

def save_page(pdf, item):
    fig = plt.figure(figsize=(11.69, 8.27), facecolor="#f4f7fb")
    fig.text(.05, .94, "DASHBOARD CONTÁBIL", fontsize=19, fontweight="bold", color="#17324d")
    fig.text(.05, .90, item["empresa"], fontsize=13, color="#31536d")
    fig.text(.95, .90, item["mes"], fontsize=12, ha="right", color="#31536d")
    cards = [
        ("Faturamento do relatório", money(item.get("faturamento_relatorio"))),
        ("Valor contábil das saídas", money(item.get("vendas_total") if item.get("tem_vendas") else None)),
        ("Impostos do mês", money(item.get("impostos_total") if item.get("tem_impostos") else None)),
        ("Notas únicas / clientes", f'{item["notas_unicas"]} / {item["clientes_unicos"]}' if item.get("tem_vendas") else "Sem dados de vendas"),
    ]
    for i, (label, value) in enumerate(cards):
        x = .05 + i * .23
        fig.text(x, .82, label, fontsize=9, color="#557086")
        fig.text(x, .77, value, fontsize=13, fontweight="bold", color="#17324d")
    ax1 = fig.add_axes([.07, .43, .42, .27])
    labels, values = [], []
    if item.get("faturamento_relatorio") is not None:
        labels.append("Faturamento")
        values.append(item["faturamento_relatorio"])
    if item.get("tem_vendas"):
        labels.append("Saídas (valor contábil)")
        values.append(item["vendas_total"])
    if labels:
        ax1.bar(labels, values, color=["#168b8b", "#4e78a0"][:len(labels)])
        ax1.set_title("Receita e saídas informadas", loc="left", fontsize=11, color="#17324d")
        ax1.tick_params(axis="x", labelrotation=8, labelsize=8)
        ax1.ticklabel_format(axis="y", style="plain")
        ax1.grid(axis="y", alpha=.2)
    else:
        ax1.text(.5, .5, "Sem dados de faturamento ou saídas", ha="center", va="center")
        ax1.axis("off")
    ax2 = fig.add_axes([.55, .43, .39, .27])
    state_rows = item.get("vendas_por_uf", [])
    if state_rows:
        state_rows = list(reversed(state_rows[:7]))
        ax2.barh([x["uf"] for x in state_rows], [x["valor"] for x in state_rows], color="#168b8b")
        ax2.set_title("Saídas por UF", loc="left", fontsize=11, color="#17324d")
        ax2.tick_params(labelsize=8)
        ax2.grid(axis="x", alpha=.2)
    else:
        ax2.text(.5, .5, "Sem dados de vendas por UF", ha="center", va="center")
        ax2.axis("off")
    ax3 = fig.add_axes([.05, .08, .42, .28])
    ax3.axis("off")
    ax3.set_title("Principais clientes nas saídas", loc="left", fontsize=11, color="#17324d")
    clients = item.get("principais_clientes", [])
    table_data = [[x["cliente"][:38], money(x["valor"])] for x in clients] or [["Sem dados", ""]]
    ax3.table(cellText=table_data, colLabels=["Cliente", "Valor contábil"], loc="upper left", cellLoc="left", colWidths=[.65, .3])
    ax4 = fig.add_axes([.53, .08, .42, .28])
    ax4.axis("off")
    ax4.set_title("Tributos por categoria", loc="left", fontsize=11, color="#17324d")
    taxes = item.get("categorias_impostos", [])
    tax_data = [[x["categoria"][:35], money(x["valor"])] for x in taxes[:6]] or [["Sem dados de tributos", ""]]
    ax4.table(cellText=tax_data, colLabels=["Categoria", "Débito"], loc="upper left", cellLoc="left", colWidths=[.65, .3])
    fig.text(.05, .025, "Conferência: totais de fontes distintas podem divergir. Ausência de registro é exibida como sem dado, não como zero.", fontsize=7, color="#667b8b")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)

with PdfPages(output_dir / "dashboards_lote.pdf") as pdf:
    for item in panels:
        save_page(pdf, item)

summary_path = output_dir / "conferencia.csv"
with summary_path.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.writer(f, delimiter=";")
    writer.writerow(["Empresa", "CNPJ", "Mês", "Faturamento relatório", "Valor contábil saídas", "Diferença", "Impostos", "Notas únicas", "Clientes únicos", "Situação vendas", "Situação impostos"])
    for x in panels:
        writer.writerow([x["empresa"], x["cnpj"], x["mes"], x.get("faturamento_relatorio"), x.get("vendas_total") if x.get("tem_vendas") else "", x.get("diferenca_faturamento_vendas") if x.get("tem_vendas") else "", x.get("impostos_total") if x.get("tem_impostos") else "", x["notas_unicas"], x["clientes_unicos"], "Encontradas" if x.get("tem_vendas") else "Sem correspondência", "Encontrados" if x.get("tem_impostos") else "Sem correspondência"])

payload = json.dumps(panels, ensure_ascii=False).replace("</", "<\\/")
page = r"""<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Dashboard contábil multiempresa</title>
<style>
body{font:15px Segoe UI,Arial,sans-serif;background:#f3f6fa;color:#17324d;margin:0}.wrap{max-width:1100px;margin:auto;padding:28px}.head{background:#17324d;color:white;padding:24px;border-radius:14px}.head h1{margin:0 0 8px}.filters,.cards,.grid{display:grid;gap:14px}.filters{grid-template-columns:2fr 1fr;background:white;padding:16px;margin:18px 0;border-radius:12px}.cards{grid-template-columns:repeat(4,1fr)}.card,.panel{background:white;padding:18px;border-radius:12px;box-shadow:0 2px 10px #17324d12}.card small{color:#61798a}.card strong{display:block;font-size:21px;margin-top:8px}.grid{grid-template-columns:1fr 1fr;margin-top:14px}.bar{display:flex;align-items:center;gap:8px;margin:8px 0}.bar span{width:38px}.fill{height:16px;background:#168b8b;border-radius:4px}.row{display:flex;justify-content:space-between;border-bottom:1px solid #e8eef2;padding:8px 0}select,button{padding:10px;border:1px solid #c8d5df;border-radius:7px;font:inherit}button{background:#168b8b;color:white;border:0;cursor:pointer}.muted{color:#667b8b;font-size:13px}.warn{padding:12px;background:#fff4d6;border-radius:8px;margin-top:14px}@media print{body{background:white}.wrap{padding:10px}.filters button{display:none}.card,.panel{box-shadow:none;border:1px solid #ddd}.head{background:#17324d!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
</style><div class="wrap"><div class="head"><h1>Dashboard Contábil</h1><div>Visão mensal por empresa · Data Engine</div></div>
<div class="filters"><label>Empresa<br><select id="company"></select></label><label>Mês<br><select id="month"></select></label><div><button onclick="window.print()">Salvar seleção em PDF</button></div></div>
<div id="dashboard"></div><p class="muted">Os filtros mostram apenas os meses presentes nas fontes desta execução. “Sem dado” significa ausência de registro correspondente.</p></div>
<script>const DATA=__DATA__;const $=id=>document.getElementById(id);const esc=s=>String(s??"").replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));const fmt=n=>n==null?'Sem dado':new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(n);const company=$('company'),month=$('month');
company.innerHTML=[...new Set(DATA.map(x=>x.empresa))].sort().map(x=>`<option>${esc(x)}</option>`).join('');month.innerHTML=[...new Set(DATA.map(x=>x.mes))].sort().map(x=>`<option>${esc(x)}</option>`).join('');
function render(){const x=DATA.find(a=>a.empresa===company.value&&a.mes===month.value);if(!x){$('dashboard').innerHTML='';return}const cards=[['Faturamento do relatório',fmt(x.faturamento_relatorio)],['Valor contábil das saídas',x.tem_vendas?fmt(x.vendas_total):'Sem dado'],['Impostos do mês',x.tem_impostos?fmt(x.impostos_total):'Sem dado'],['Notas únicas / clientes',x.tem_vendas?`${x.notas_unicas} / ${x.clientes_unicos}`:'Sem dado']];const max=Math.max(1,...(x.vendas_por_uf||[]).map(a=>a.valor));$('dashboard').innerHTML=`<div class="cards">${cards.map(a=>`<div class="card"><small>${esc(a[0])}</small><strong>${esc(a[1])}</strong></div>`).join('')}</div><div class="grid"><div class="panel"><h3>Saídas por UF</h3>${(x.vendas_por_uf||[]).map(a=>`<div class="bar"><span>${esc(a.uf)}</span><div class="fill" style="width:${Math.max(2,100*a.valor/max)}%"></div><small>${esc(fmt(a.valor))}</small></div>`).join('')||'<p>Sem dados</p>'}</div><div class="panel"><h3>Principais clientes</h3>${(x.principais_clientes||[]).map(a=>`<div class="row"><span>${esc(a.cliente)}</span><b>${esc(fmt(a.valor))}</b></div>`).join('')||'<p>Sem dados</p>'}</div><div class="panel"><h3>Tributos por categoria</h3>${(x.categorias_impostos||[]).map(a=>`<div class="row"><span>${esc(a.categoria)}</span><b>${esc(fmt(a.valor))}</b></div>`).join('')||'<p>Sem dados de tributos para o mês/CNPJ.</p>'}</div><div class="panel"><h3>Conferência das fontes</h3><div class="row"><span>Diferença faturamento − valor contábil de saídas</span><b>${esc(fmt(x.diferenca_faturamento_vendas))}</b></div><p class="muted">Os dois totais vêm de relatórios diferentes e podem usar critérios distintos. Use a diferença como sinal de conferência.</p><div class="warn">Vendas: ${x.tem_vendas?'correspondência encontrada':'sem correspondência'} · Impostos: ${x.tem_impostos?'correspondência encontrada':'sem correspondência'}</div></div></div>`}
company.onchange=render;month.onchange=render;render();</script></html>""".replace("__DATA__", payload)
(output_dir / "dashboard_interativo.html").write_text(page, encoding="utf-8")

unmatched = data.get("vendas_sem_correspondencia", [])
(output_dir / "leia-me.txt").write_text(
    "Dashboard multiempresa gerado pelo Data Engine.\n"
    "dashboard_interativo.html: filtre empresa e mês; use Salvar seleção em PDF e escolha Imprimir/Salvar como PDF no navegador.\n"
    "dashboards_lote.pdf: uma página por empresa e mês encontrado nesta execução.\n"
    "conferencia.csv: totais e cobertura das fontes para revisão.\n"
    "Observação: o workbook Nóbrega foi usado apenas como referência visual; não há dados da Nóbrega nas entradas deste teste.\n"
    + ("Nomes de vendas sem correspondência automática: " + ", ".join(unmatched) + "\n" if unmatched else "")
    + "Ausência de dados é exibida como sem dado e não é convertida em zero.\n",
    encoding="utf-8",
)
'''

CONFIG = {
    "version": 2,
    "name": PROJECT_NAME,
    "inputs": [
        {"id": "faturamento", "name": "Faturamento", "paths": [BILLING_PATH], "code": BILLING_CODE},
        {"id": "impostos", "name": "Impostos", "paths": [TAX_PATH], "code": TAX_CODE},
        {"id": "vendas", "name": "Vendas", "paths": [SALES_PATH], "code": SALES_CODE},
    ],
    "process_code": PROCESS_CODE,
    "output_code": OUTPUT_CODE,
    "output_path": str(APP_DIR / "data" / "projetos" / "Dashboard Contábil Multiempresa"),
}


def main() -> None:
    project = engine.project_path(PROJECT_ID)
    project.mkdir(parents=True, exist_ok=True)
    (project / "inputs").mkdir(exist_ok=True)
    (project / "runs").mkdir(exist_ok=True)
    engine.save_config(PROJECT_ID, CONFIG)
    source_dir = project / "codigo_fonte"
    source_dir.mkdir(exist_ok=True)
    for filename, source in (
        ("entrada_faturamento.py", BILLING_CODE),
        ("entrada_impostos.py", TAX_CODE),
        ("entrada_vendas.py", SALES_CODE),
        ("processamento_geral.py", PROCESS_CODE),
        ("saida_dashboard.py", OUTPUT_CODE),
    ):
        (source_dir / filename).write_text(source, encoding="utf-8")
    (project / "LEIA-ME.txt").write_text(
        "DASHBOARD CONTÁBIL MULTIEMPRESA - COMO USAR\n\n"
        "1. Abra o Data Engine pelo arquivo Abrir_Data_Engine.bat.\n"
        "2. Na lista Projetos, escolha Dashboard Contábil Multiempresa. Se ele já estava aberto, atualize a página do navegador.\n"
        "3. Na aba Entradas, confirme os caminhos e os códigos das três fontes: Faturamento, Impostos e Vendas.\n"
        "4. Na aba Processamento e saída, os códigos de cruzamento e geração de arquivos já estão preenchidos.\n"
        "5. Clique Executar projeto. O resultado será baixado como ZIP e também copiado para a pasta de saída configurada.\n\n"
        "ARQUIVOS GERADOS\n"
        "- dashboard_interativo.html: filtros de empresa e mês; o botão Salvar seleção em PDF abre a impressão do navegador.\n"
        "- dashboards_lote.pdf: uma página por empresa e mês encontrado, para salvar ou revisar em conjunto.\n"
        "- conferencia.csv: compara o faturamento do relatório com o valor contábil das saídas e mostra a cobertura das fontes.\n"
        "- leia-me.txt: resumo da execução e nomes de vendas sem correspondência automática, se houver.\n\n"
        "As fontes atuais contêm faturamento e vendas de agosto de 2026; por isso, o filtro de mês mostra agosto. Os códigos aceitam vários arquivos por entrada, então você pode acrescentar novos arquivos mensais nos caminhos da entrada e executar novamente. Prefira pastas separadas por tipo de fonte.\n"
        "A planilha 008 - Nóbrega - Dash.xlsx foi usada apenas como referência de organização. A empresa Nóbrega não aparece nas três fontes deste teste; não use os resultados como validação da planilha Nóbrega.\n"
        "A ausência de dados é exibida como sem dado, nunca presumida como zero. O valor contábil das saídas e o faturamento do relatório podem ter critérios diferentes; revise a diferença na conferência.\n"
        "Os arquivos fonte editáveis estão em codigo_fonte. Os caminhos podem ser alterados nos campos de entrada.\n",
        encoding="utf-8",
    )
    print(f"Projeto configurado: {project}")
    print(f"Planilha de referência identificada (não usada como fonte): {REFERENCE_PATH}")


if __name__ == "__main__":
    main()
