# Streamlit Chat Interno + Integração com n8n (versão estável)
# -------------------------------------------------
# ▶️ Como usar
# 1) Salve este arquivo como: streamlit-chat-interno-n8n.py
# 2) Instale: pip3 install streamlit requests
# 3) Rode:    streamlit run streamlit-chat-interno-n8n.py
# -------------------------------------------------

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

# ----------------------------
# Configuração da página
# ----------------------------
st.set_page_config(
    page_title="Chat Interno • n8n",
    page_icon="💬",
    layout="wide",
)

st.markdown(
    """
    <style>
    .small {font-size: 0.82rem; color: #9ca3af}
    .ok {color:#16a34a}
    .err {color:#dc2626}
    .pill {display:inline-block;padding:2px 8px;border-radius:999px;background:#eef2ff;color:#3730a3;font-size:12px;margin-left:6px}
    .section {border:1px solid #e5e7eb;border-radius:14px;padding:14px 16px;margin-bottom:12px;background:#111827}
    .chatbox {min-height:60vh}
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------
# Helpers
# ----------------------------

def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Lê secrets do Streamlit ou variável de ambiente."""
    try:
        return st.secrets.get(key, default)
    except Exception:
        return os.getenv(key, default)

N8N_WEBHOOK_URL: str = get_secret(
    "N8N_WEBHOOK_URL",
    "https://micheliniautomacoes2.app.n8n.cloud/webhook/8c7b1336-0183-41f2-943c-c3fd2a2766f3",
)
OPTIONAL_PASSCODE: str = get_secret("OPTIONAL_PASSCODE", "")


def format_ts(ts: Optional[str]) -> str:
    """Formata ISO -> dd/mm HH:MM; se falhar usa agora."""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else datetime.now()
    except Exception:
        dt = datetime.now()
    return dt.strftime("%d/%m %H:%M")


def send_json_to_n8n(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """POST JSON ao webhook e retorna dict seguro."""
    r = requests.post(url, json=payload, timeout=60)
    try:
        return r.json()
    except Exception:
        body = (r.text or "").strip()
        return {"text": body} if body else {}


def send_multipart_to_n8n(url: str, payload: Dict[str, Any], files: Dict[str, Any]) -> Dict[str, Any]:
    """POST multipart (arquivo + campo json) ao webhook."""
    r = requests.post(url, data={"json": json.dumps(payload)}, files=files, timeout=60)
    try:
        return r.json()
    except Exception:
        body = (r.text or "").strip()
        return {"text": body} if body else {}

# ----------------------------
# Autenticação simples (opcional)
# ----------------------------
if OPTIONAL_PASSCODE:
    with st.sidebar:
        st.subheader("🔐 Acesso")
        pwd = st.text_input("Passcode", type="password")
        if pwd != OPTIONAL_PASSCODE:
            st.info("Informe o passcode para usar o painel.")
            st.stop()

# ----------------------------
# Estado da sessão
# ----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []  # type: List[Dict[str, Any]]

if "user_profile" not in st.session_state:
    st.session_state.user_profile = {
        "name": "User",
        "email": "user@empresa.com",
        "tz": "America/Sao_Paulo",
    }

# ----------------------------
# Sidebar: Config + Ações rápidas
# ----------------------------
with st.sidebar:
    st.header("⚙️ Config")
    N8N_WEBHOOK_URL = st.text_input(
        "n8n Webhook URL",
        value=N8N_WEBHOOK_URL,
        placeholder="https://seu-n8n/webhook/streamlit-interno",
    )
    st.caption("Defina também em Secrets no deploy.")

    colA, colB = st.columns(2)
    with colA:
        ping = st.button("Testar conexão")
    with colB:
        clear = st.button("Limpar histórico")

    if clear:
        st.session_state.messages = []
        st.success("Histórico limpo.")

    if ping and N8N_WEBHOOK_URL:
        try:
            r = requests.post(N8N_WEBHOOK_URL, json={"ping": True}, timeout=10)
            st.write(f"Status: {r.status_code}")
            if r.ok:
                st.markdown("<span class='ok'>Conectado ao n8n</span>", unsafe_allow_html=True)
            else:
                st.markdown("<span class='err'>Falha ao conectar</span>", unsafe_allow_html=True)
        except Exception as e:
            st.markdown(f"<span class='err'>Erro: {e}</span>", unsafe_allow_html=True)

    st.divider()
    st.subheader("⚡ Ações rápidas")

    envio_modo = st.radio(
        "Modo de envio",
        ["Mensagem única (recomendado)", "JSON (intent avançado)"] ,
        index=0,
        help=(
            "Mensagem única: monta uma frase completa pro agente e envia como se você tivesse escrito tudo. "
            "JSON: envia um payload estruturado para rotas específicas no n8n."
        ),
    )

    # ---------- Geração de Documento ----------
    with st.expander("📝 Gerar Documento (por template)", expanded=False):
        doc_tipo = st.selectbox(
            "Tipo de documento",
            ["Proposta", "Contrato PJ", "Contrato PF", "Ata de reunião", "Briefing"],
            key="tipo_doc",
        )
        cliente = st.text_input("Cliente / Parte", key="doc_cliente")
        prazo = st.text_input("Prazo / Vigência", placeholder="12 meses", key="doc_prazo")
        valor = st.text_input("Valor", placeholder="R$ 10.000,00", key="doc_valor")
        observ = st.text_area("Observações adicionais", key="doc_obs")
        gerar = st.button("Enviar", key="btn_doc")
        if gerar:
            if envio_modo.startswith("Mensagem única"):
                msg = (
                    f"Por favor, GERAR DOCUMENTO com estes dados: "
                    f"tipo: {doc_tipo}; cliente: {cliente or '-'}; prazo: {prazo or '-'}; valor: {valor or '-'}; "
                    f"observações: {observ or '-'}."
                )
                st.session_state.messages.append({"role": "user", "content": msg, "ts": datetime.now().isoformat()})
                data = send_json_to_n8n(N8N_WEBHOOK_URL, {
                    "source": "streamlit",
                    "actor": st.session_state.user_profile,
                    "message": msg,
                    "history": st.session_state.messages[-10:],
                })
                reply = data.get("reply") or data.get("text") or "✅ Solicitação enviada ao n8n."
                st.session_state.messages.append({"role": "assistant", "content": reply, "ts": datetime.now().isoformat()})
                st.success("Mensagem enviada ao agente.")
            else:
                payload = {
                    "source": "streamlit",
                    "actor": st.session_state.user_profile,
                    "intent": "gerar_documento",
                    "payload": {
                        "tipo": doc_tipo,
                        "cliente": cliente,
                        "prazo": prazo,
                        "valor": valor,
                        "observacoes": observ,
                    },
                    "history": st.session_state.messages[-10:],
                }
                data = send_json_to_n8n(N8N_WEBHOOK_URL, payload)
                msg_ok = data.get("reply") or data.get("text") or "✅ Documento solicitado."
                st.success(msg_ok)
                st.session_state.messages.append({"role": "assistant", "content": msg_ok, "ts": datetime.now().isoformat()})

    # ---------- Cadastro Rápido ----------
    with st.expander("📇 Cadastro Rápido (Cliente)", expanded=False):
        razao = st.text_input("Razão Social / Nome", key="cad_razao")
        cnpj_cpf = st.text_input("CNPJ/CPF", key="cad_doc")
        contato_nome = st.text_input("Contato - Nome", key="cad_nome")
        contato_email = st.text_input("Contato - Email", key="cad_email")
        contato_tel = st.text_input("Contato - Telefone", key="cad_tel")
        plano = st.selectbox("Plano", ["BASIC", "PRO", "ENTERPRISE"], key="cad_plano")
        obs = st.text_area("Observações", key="cad_obs")
        enviar_cad = st.button("Enviar cadastro", key="btn_cad")
        if enviar_cad:
            if envio_modo.startswith("Mensagem única"):
                msg = (
                    "Quero CADASTRAR CLIENTE com os seguintes dados: "
                    f"nome/razão social: {razao or '-'}; CNPJ/CPF: {cnpj_cpf or '-'}; "
                    f"contato (nome): {contato_nome or '-'}; contato (email): {contato_email or '-'}; contato (telefone): {contato_tel or '-'}; "
                    f"plano: {plano}; observações: {obs or '-'}."
                )
                st.session_state.messages.append({"role": "user", "content": msg, "ts": datetime.now().isoformat()})
                data = send_json_to_n8n(N8N_WEBHOOK_URL, {
                    "source": "streamlit",
                    "actor": st.session_state.user_profile,
                    "message": msg,
                    "history": st.session_state.messages[-10:],
                })
                reply = data.get("reply") or data.get("text") or "✅ Solicitação enviada ao n8n."
                st.session_state.messages.append({"role": "assistant", "content": reply, "ts": datetime.now().isoformat()})
                st.success("Mensagem enviada ao agente.")
            else:
                payload = {
                    "source": "streamlit",
                    "actor": st.session_state.user_profile,
                    "intent": "cadastro_cliente",
                    "payload": {
                        "razao_social": razao,
                        "cnpj_cpf": cnpj_cpf,
                        "contato": {
                            "nome": contato_nome,
                            "email": contato_email,
                            "telefone": contato_tel,
                        },
                        "plano": plano,
                        "observacoes": obs,
                    },
                    "history": st.session_state.messages[-10:],
                }
                data = send_json_to_n8n(N8N_WEBHOOK_URL, payload)
                msg_ok = data.get("reply") or data.get("text") or "✅ Cadastro criado."
                st.success(msg_ok)
                st.session_state.messages.append({"role": "assistant", "content": msg_ok, "ts": datetime.now().isoformat()})

    # ---------- Upload de Arquivo ----------
    with st.expander("📎 Enviar arquivo para processamento", expanded=False):
        up = st.file_uploader("Selecione um arquivo (PDF, DOCX, XLSX, imagens)", type=None)
        observ_file = st.text_input("Instruções para o arquivo (opcional)", key="file_obs")
        acionar = st.button("Enviar arquivo", key="btn_file")
        if acionar:
            if not up:
                st.warning("Selecione um arquivo.")
            else:
                content = up.read()
                files = {"file": (up.name, content)}
                if envio_modo.startswith("Mensagem única"):
                    msg = f"Por favor PROCESSAR ARQUIVO '{up.name}'. Instruções: {observ_file or '-'}"
                    payload = {
                        "source": "streamlit",
                        "actor": st.session_state.user_profile,
                        "message": msg,
                        "filename": up.name,
                        "history": st.session_state.messages[-10:],
                    }
                else:
                    payload = {
                        "source": "streamlit",
                        "actor": st.session_state.user_profile,
                        "intent": "processar_arquivo",
                        "filename": up.name,
                        "observacoes": observ_file,
                        "history": st.session_state.messages[-10:],
                    }
                data = send_multipart_to_n8n(N8N_WEBHOOK_URL, payload, files)
                msg_resp = data.get("reply") or data.get("text") or "📎 Arquivo enviado para processamento."
                if envio_modo.startswith("Mensagem única"):
                    st.session_state.messages.append({"role": "user", "content": payload.get("message", "(envio de arquivo)"), "ts": datetime.now().isoformat()})
                st.session_state.messages.append({"role": "assistant", "content": msg_resp, "ts": datetime.now().isoformat()})
                st.success("Arquivo enviado ao agente.")

    st.divider()
    with st.expander("❓ Ajuda rápida", expanded=False):
        st.markdown(
            """
            **Exemplos úteis**
            - Gerar contrato para Cliente ACME, prazo 12 meses, valor R$ 10.000 (use o formulário ou digite)
            - Cadastrar cliente com nome, CNPJ/CPF, contatos e plano (formulário → mensagem única)
            - Processar arquivo com instruções (upload + instruções)
            """
        )

# ----------------------------
# Main: Chat em tela cheia
# ----------------------------
st.title("💬 Chat Interno + Cadastros (Streamlit ↔ n8n)")

chat_container = st.container()
with chat_container:
    st.subheader("Conversa")
    st.markdown("<div class='chatbox'></div>", unsafe_allow_html=True)

    msgs = sorted(st.session_state.messages, key=lambda m: m.get("ts", ""))
    for m in msgs:
        with st.chat_message(m.get("role", "assistant")):
            content = m.get("content", "")
            st.markdown(content)
            st.caption(f"{m.get('role','')} • {format_ts(m.get('ts'))}")

prompt = st.chat_input("Digite sua mensagem… (/ajuda para sugestões)")

if prompt:
    user_msg = {
        "role": "user",
        "content": prompt,
        "ts": datetime.now().isoformat(),
    }
    st.session_state.messages.append(user_msg)
    with st.chat_message("user"):
        st.markdown(prompt)
        st.caption(f"user • {format_ts(user_msg['ts'])}")

    payload = {
        "source": "streamlit",
        "actor": st.session_state.user_profile,
        "message": prompt,
        "history": st.session_state.messages[-10:],
        "tz": st.session_state.user_profile.get("tz", "America/Sao_Paulo"),
    }

    try:
        data = send_json_to_n8n(N8N_WEBHOOK_URL, payload)
        bot_text = data.get("reply") or data.get("text") or "✅ Solicitação enviada ao n8n."
    except Exception as e:
        bot_text = f"❌ Erro ao contatar n8n: {e}"

    bot_msg = {"role": "assistant", "content": bot_text, "ts": datetime.now().isoformat()}
    st.session_state.messages.append(bot_msg)
    with st.chat_message("assistant"):
        st.markdown(bot_text)
        st.caption(f"assistant • {format_ts(bot_msg['ts'])}")
