import mimetypes
import os
from pathlib import Path

import streamlit as st
import engine


def save_widget_state(project_id: str) -> None:
    current = engine.load_config(project_id)
    project_key = f"project-name-{project_id}"
    if project_key in st.session_state:
        current["name"] = st.session_state[project_key]
    for index, item in enumerate(current["inputs"]):
        input_key = item.get("id", f"entrada-{index + 1}")
        name_key = f"name-{project_id}-{input_key}"
        paths_key = f"paths-{project_id}-{input_key}"
        code_key = f"code-{project_id}-{input_key}"
        if name_key in st.session_state:
            item["name"] = st.session_state[name_key]
        if paths_key in st.session_state:
            item["paths"] = [line.strip() for line in st.session_state[paths_key].splitlines() if line.strip()]
        if code_key in st.session_state:
            item["code"] = st.session_state[code_key]
    for config_key, widget_key in (
        ("process_code", f"process-{project_id}"),
        ("output_code", f"output-{project_id}"),
        ("output_path", f"outpath-{project_id}"),
    ):
        if widget_key in st.session_state:
            current[config_key] = st.session_state[widget_key]
    engine.save_config(project_id, current)


def save_uploaded_files(project_id: str, input_id: str) -> None:
    config = engine.load_config(project_id)
    item = next((entry for entry in config["inputs"] if entry.get("id") == input_id), None)
    uploaded = st.session_state.get(f"upload-{project_id}-{input_id}") or []
    if not item or not uploaded:
        return

    existing_content = {}
    for raw_path in item.get("paths", []):
        saved_path = Path(raw_path)
        if saved_path.is_file():
            existing_content[saved_path.name.casefold()] = saved_path.read_bytes()

    pending = []
    seen_names = set()
    for uploaded_file in uploaded:
        filename = Path(uploaded_file.name).name
        key = filename.casefold()
        content = uploaded_file.getvalue()
        if key in seen_names:
            continue
        seen_names.add(key)
        if existing_content.get(key) != content:
            pending.append(uploaded_file)

    if not pending:
        return

    stored_paths = engine.add_uploaded_files(project_id, input_id, pending)
    item["paths"] = list(dict.fromkeys(item.get("paths", []) + stored_paths))
    st.session_state[f"paths-{project_id}-{input_id}"] = "\n".join(item["paths"])
    engine.save_config(project_id, config)
    st.toast("Arquivo(s) copiado(s) para esta entrada.")

st.set_page_config(page_title="Data Engine", page_icon="⚙️", layout="wide")
engine.ensure_demo_project()
web_mode = os.getenv("DATA_ENGINE_MODE", "local").strip().lower() == "web"
st.markdown("""
<style>
.block-container{padding-top:1.6rem;padding-bottom:2.5rem;max-width:1420px}
[data-testid="stAppViewContainer"]{background:var(--background-color)}
[data-testid="stSidebar"]{background:var(--secondary-background-color);border-right:1px solid #77808c}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"]{color:var(--text-color)!important}
[data-testid="stSidebar"] input{background:var(--background-color)!important;color:var(--text-color)!important;border-color:#77808c!important}
[data-testid="stSidebar"] [data-baseweb="select"]>div{background:var(--background-color)!important;color:var(--text-color)!important;border-color:#77808c!important}
[data-testid="stSidebar"] [data-baseweb="select"] *{color:var(--text-color)!important}
[data-testid="stSidebar"] [data-baseweb="menu"],[data-testid="stSidebar"] [role="option"]{background:var(--secondary-background-color)!important;color:var(--text-color)!important}
[data-testid="stSidebar"] button{background:var(--secondary-background-color)!important;color:var(--text-color)!important;border:1px solid #77808c!important}
.hero{padding:1.2rem 1.5rem;border-radius:14px;background:linear-gradient(120deg,#17324d,#087f83);color:#fff;margin-bottom:1rem;border:1px solid #31596a}
.hero h1{color:#fff;margin:0;font-size:2rem}.hero p{color:#e5f4f4;margin:.35rem 0 0}
.flow{background:var(--secondary-background-color);border:1px solid #77808c;border-radius:12px;padding:.9rem;text-align:center;color:var(--text-color)}
[data-testid="stExpander"]{border:1px solid #77808c;border-radius:12px;background:var(--secondary-background-color)}
[data-testid="stExpander"] summary{color:var(--text-color)}
[data-testid="stTabs"] button{color:var(--text-color)}
[data-testid="stWidgetLabel"] p,[data-testid="stWidgetLabel"] label{color:var(--text-color)!important}
[data-testid="stCaptionContainer"]{color:var(--text-color)!important;opacity:.76}
[data-testid="stTextArea"] textarea,[data-testid="stTextInput"] input{border-color:#77808c}
[data-testid="stFileUploader"] section{border-color:#77808c;background:var(--secondary-background-color)}
.stButton>button,[data-testid="stFormSubmitButton"] button{border-radius:9px;min-height:2.65rem}
.stButton>button:not([kind="primary"]),[data-testid="stFormSubmitButton"] button{background:var(--secondary-background-color);color:var(--text-color);border:1px solid #77808c}
[data-testid="stBaseButton-primary"],.stButton>button[kind="primary"]{background:var(--primary-color)!important;color:var(--text-color)!important;border:1px solid var(--primary-color)!important}
[data-testid="stDownloadButton"] button{background:var(--primary-color);color:var(--text-color);border:1px solid var(--primary-color)}
@media (max-width: 850px){.block-container{padding:1rem}.hero h1{font-size:1.6rem}}
</style>
<div class="hero"><h1>Data Engine</h1><p>Uma estrutura para você definir o que fazer com seus dados.</p></div>
""", unsafe_allow_html=True)

projects = engine.list_projects()
with st.sidebar:
    st.header("Projetos")
    labels = {f"{item['name']} · {item['id'][-6:]}": item["id"] for item in projects}
    if labels:
        preferred = st.session_state.get("selected_project")
        initial = next((i for i, project_key in enumerate(labels) if labels[project_key] == preferred), 0)
        selected = st.selectbox("Abrir projeto", list(labels), index=initial)
        project_id = labels[selected]
        st.session_state["selected_project"] = project_id
    else:
        project_id = None
    with st.form("new-project", clear_on_submit=True):
        name = st.text_input("Nome do novo projeto", placeholder="Ex.: Consolidar extratos")
        create = st.form_submit_button("Criar projeto", use_container_width=True)
    if create and name.strip():
        project_id = engine.create_project(name)
        st.session_state["selected_project"] = project_id
        st.rerun()
    if web_mode:
        st.caption("Modo web: arquivos enviados são usados somente na execução atual; os códigos e configurações ficam no projeto.")
    else:
        st.caption("Os projetos e arquivos ficam neste computador.")

if not project_id:
    st.info("Crie um projeto para começar.")
    st.stop()

config = engine.load_config(project_id)
config["name"] = st.text_input("Nome do projeto", value=config.get("name", ""), key=f"project-name-{project_id}", on_change=save_widget_state, args=(project_id,))
st.markdown('<div class="flow"><b>ENTRADAS</b>　→　<b>PROCESSAMENTO OPCIONAL</b>　→　<b>SAÍDA</b><br>Use apenas as etapas necessárias para o seu trabalho.</div>', unsafe_allow_html=True)

inputs_tab, process_tab, history_tab, about_tab = st.tabs([
    "1 · Entradas",
    "2 · Processamento e saída",
    "Histórico",
    "Sobre e manuais",
])
with inputs_tab:
    st.subheader("Entradas de dados")
    st.caption("Informe um ou mais arquivos ou pastas. Cada entrada tem seu próprio código para ler e preparar esses arquivos.")
    if st.button("＋ Adicionar entrada", key=f"add-{project_id}"):
        n = len(config["inputs"]) + 1
        config["inputs"].append({"id": f"entrada-{n}", "name": f"Entrada {n}", "paths": [], "code": ""})
        engine.save_config(project_id, config)
        st.rerun()
    for i, item in enumerate(config["inputs"]):
        item.setdefault("paths", [])
        input_key = item.setdefault("id", f"entrada-{i+1}")
        expander_title = item.get("name", f"Entrada {i+1}")
        if not web_mode:
            expander_title += f" · {len(item['paths'])} caminho(s)"
        with st.expander(expander_title, expanded=(i == 0)):
            item["name"] = st.text_input("Nome desta entrada", value=item.get("name", f"Entrada {i+1}"), key=f"name-{project_id}-{input_key}", on_change=save_widget_state, args=(project_id,))
            st.checkbox("Incluir esta entrada na próxima execução", value=True, key=f"run-input-{project_id}-{input_key}")
            source_col, code_col = st.columns([1, 2], gap="large")
            with source_col:
                if not web_mode:
                    paths_text = st.text_area("Caminhos dos arquivos ou pastas", value="\n".join(item["paths"]), height=112, placeholder=r"C:\Dados\Extratos\2026\Janeiro.ofx", key=f"paths-{project_id}-{input_key}", on_change=save_widget_state, args=(project_id,), help="Informe um caminho por linha. Pastas são pesquisadas automaticamente.")
                    item["paths"] = [line.strip() for line in paths_text.splitlines() if line.strip()]
                else:
                    st.caption("Na versão web, selecione os arquivos no seu dispositivo. Caminhos do seu computador não são acessíveis pelo servidor.")
                upload_key = f"upload-{project_id}-{input_key}"
                if web_mode:
                    upload_cycle_key = f"upload-cycle-{project_id}-{input_key}"
                    st.session_state.setdefault(upload_cycle_key, 0)
                    upload_key = f"{upload_key}-{st.session_state[upload_cycle_key]}"
                st.file_uploader(
                    "Escolher arquivos para esta entrada",
                    accept_multiple_files=True,
                    key=upload_key,
                    on_change=None if web_mode else save_uploaded_files,
                    args=() if web_mode else (project_id, input_key),
                )
                if web_mode:
                    st.caption("Os arquivos selecionados serão usados somente nesta execução. Envie novamente na próxima rodada.")
            with code_col:
                item["code"] = st.text_area("Código Python desta entrada", value=item.get("code", ""), height=310, key=f"code-{project_id}-{input_key}", help="O motor entrega `files`, uma lista de objetos Path, e espera que o código defina `result`.", on_change=save_widget_state, args=(project_id,))
            if st.button("Excluir esta entrada", key=f"delete-{project_id}-{input_key}"):
                config["inputs"].pop(i)
                engine.save_config(project_id, config)
                st.rerun()
    if st.button("Salvar projeto", key=f"save-inputs-{project_id}"):
        engine.save_config(project_id, config)
        st.success("Projeto salvo.")
    if not config["inputs"]:
        st.info("Adicione uma entrada. Uma única entrada já pode resolver uma conversão simples.")

with process_tab:
    st.subheader("Processamento geral opcional")
    st.caption("Os resultados das entradas selecionadas chegam em `inputs`, organizados pelo nome de cada entrada. Entradas desmarcadas não estarão disponíveis nesta execução.")
    st.caption("A seleção de entradas não pula esta etapa: o processamento é executado normalmente com as entradas marcadas. Defina `result` com os dados preparados.")
    config["process_code"] = st.text_area("Código de processamento", value=config.get("process_code", ""), height=240, key=f"process-{project_id}", on_change=save_widget_state, args=(project_id,))
    st.subheader("Saída")
    st.caption("A variável `data` contém os dados preparados. `output_dir` é uma pasta Path para os arquivos finais.")
    config["output_code"] = st.text_area("Código para gerar os arquivos finais", value=config.get("output_code", ""), height=220, key=f"output-{project_id}", on_change=save_widget_state, args=(project_id,))
    if not config["output_code"].strip():
        st.info("Sem código de saída, o Data Engine guarda os dados preparados em um arquivo dados.json.")
    if not web_mode:
        config["output_path"] = st.text_input("Copiar os resultados para esta pasta (opcional)", value=config.get("output_path", ""), placeholder=r"C:\Resultados\Processo", key=f"outpath-{project_id}", on_change=save_widget_state, args=(project_id,))
    else:
        st.caption("Na versão web, os arquivos finais são baixados pelo navegador.")
    if st.button("Salvar projeto", key=f"save-processing-{project_id}"):
        engine.save_config(project_id, config)
        st.success("Projeto salvo.")

with history_tab:
    st.subheader("Execuções recentes")
    runs = engine.read_history(project_id)
    if runs:
        st.dataframe(runs, use_container_width=True, hide_index=True)
    else:
        st.caption("O histórico deste projeto aparecerá aqui.")

with about_tab:
    st.subheader("Sobre o Data Engine")
    st.write(
        "O Data Engine é uma estrutura reutilizável para ler arquivos, preparar dados e gerar os resultados que você precisa. "
        "O aplicativo não traz regras prontas para cada banco ou empresa: você descreve o objetivo e usa códigos próprios em cada projeto."
    )

    st.markdown("#### Como funciona")
    st.markdown(
        "1. **Entradas:** informe arquivos ou pastas e o código que lê cada fonte. "
        "Se houver leiautes diferentes, como extratos de bancos diferentes, crie uma entrada para cada leiaute.\n"
        "2. **Seleção da execução:** marque as entradas que quer usar. As desmarcadas são ignoradas nessa rodada.\n"
        "3. **Processamento:** combine as entradas selecionadas quando necessário. Pode ficar vazio se uma entrada já prepara tudo.\n"
        "4. **Saída:** gere o arquivo final, como CSV, Excel, PDF ou OFX, com o código de saída."
    )
    st.info(
        "Marcar uma entrada executa o fluxo completo para ela: o código de leitura, o processamento configurado e a saída. "
        "As entradas desmarcadas são ignoradas nessa rodada."
    )
    if web_mode:
        st.warning(
            "Modo web para validar uploads e execução: os códigos e configurações ficam no armazenamento local da aplicação e podem não sobreviver "
            "a reinicializações nem oferecer colaboração confiável. Os arquivos enviados são temporários por execução. Os blocos Python rodam no servidor com as permissões da aplicação. "
            "Para colaboração persistente, conecte armazenamento compartilhado de projetos e arquivos e defina controles de acesso "
            "antes de disponibilizar a equipe."
        )
    else:
        st.warning(
            "Esta versão roda localmente. Em uma hospedagem, o navegador envia arquivos ao servidor, mas caminhos do seu computador "
            "não ficam disponíveis nele. Os blocos Python também rodam com as permissões do servidor. A colaboração persistente exige "
            "armazenamento compartilhado de projetos e arquivos."
        )

    st.markdown("#### Como pedir os códigos a uma IA")
    st.write(
        "Explique quais arquivos você tem, como estão organizados, o que quer fazer com eles, "
        "as regras que devem ser seguidas e qual arquivo final espera. Inclua exemplos dos campos e diga como pretende conferir o resultado. "
        "Anexe o Manual para IA: ele explica as variáveis disponíveis, a seleção de entradas e onde cada código deve ser colado."
    )

    documentation_dir = Path(__file__).resolve().parent / "documentacao"
    manual_pdf = documentation_dir / "Manual_de_Integração_com_IA_do_Data_Engine_v1.3.pdf"
    manual_markdown = documentation_dir / "Manual_de_Integração_com_IA_do_Data_Engine.md"
    pdf_col, markdown_col = st.columns(2)
    with pdf_col:
        if manual_pdf.is_file():
            st.download_button(
                "Baixar Manual para IA (PDF)",
                manual_pdf.read_bytes(),
                file_name=manual_pdf.name,
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.warning("O PDF do Manual para IA não está incluído nesta instalação.")
    with markdown_col:
        if manual_markdown.is_file():
            st.download_button(
                "Baixar Manual para IA (texto)",
                manual_markdown.read_bytes(),
                file_name=manual_markdown.name,
                mime="text/markdown",
                use_container_width=True,
            )
        else:
            st.warning("A versão em texto do Manual para IA não está incluída nesta instalação.")

st.divider()
st.subheader("Executar")
run_col, note_col = st.columns([1,3])
with run_col:
    run_clicked = st.button("Executar fluxo selecionado", type="primary", use_container_width=True, disabled=not config["inputs"])
with note_col:
    st.caption("Marque as entradas desejadas nos cartões acima. O processamento e a saída serão executados com os resultados dessas entradas.")
if run_clicked:
    engine.save_config(project_id, config)
    selected_input_ids = [
        item["id"]
        for item in config["inputs"]
        if st.session_state.get(f"run-input-{project_id}-{item['id']}", True)
    ]
    uploaded_files_by_input = None
    if web_mode:
        uploaded_files_by_input = {}
        for item in config["inputs"]:
            input_id = item["id"]
            if input_id not in selected_input_ids:
                continue
            cycle_key = f"upload-cycle-{project_id}-{input_id}"
            cycle = st.session_state.get(cycle_key, 0)
            widget_key = f"upload-{project_id}-{input_id}-{cycle}"
            uploaded_files_by_input[input_id] = st.session_state.get(widget_key, [])
            st.session_state[cycle_key] = st.session_state.get(cycle_key, 0) + 1
    with st.spinner("Executando as entradas selecionadas, o processamento e a saída…"):
        try:
            download_files, logs = engine.run_project(project_id, selected_input_ids=selected_input_ids, uploaded_files_by_input=uploaded_files_by_input)
            st.success("Fluxo concluído.")
            if len(download_files) == 1 and download_files[0].suffix.lower() == ".zip":
                download_file = download_files[0]
                st.download_button(
                    "Baixar resultados ZIP",
                    download_file.read_bytes(),
                    file_name=download_file.name,
                    mime="application/zip",
                )
            elif len(download_files) == 1:
                download_file = download_files[0]
                download_mime = mimetypes.guess_type(download_file.name)[0] or "application/octet-stream"
                st.download_button(
                    f"Baixar {download_file.name}",
                    download_file.read_bytes(),
                    file_name=download_file.name,
                    mime=download_mime,
                )
            else:
                st.markdown("**Arquivos gerados**")
                download_cols = st.columns(min(len(download_files), 4))
                for index, download_file in enumerate(download_files):
                    download_mime = mimetypes.guess_type(download_file.name)[0] or "application/octet-stream"
                    with download_cols[index % len(download_cols)]:
                        st.download_button(
                            f"Baixar {download_file.name}",
                            download_file.read_bytes(),
                            file_name=download_file.name,
                            mime=download_mime,
                            key=f"download-{project_id}-{download_file.name}",
                        )
            for log in logs:
                with st.expander(log.splitlines()[0] if log else "Etapa"):
                    st.code(log or "Concluída sem mensagens.")
        except Exception as exc:
            st.error(f"A execução falhou: {exc}")
            st.info("Confira os caminhos, o código e se cada etapa definiu a variável `result` quando necessário.")
