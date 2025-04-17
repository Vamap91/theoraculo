import streamlit as st

st.title("🎈 My new app")
st.write(
    "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
)
import streamlit as st
from openai import OpenAI
import tempfile
import re
import json

# Inicializa o novo cliente da OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Configurações da página
st.set_page_config(page_title="HeatGlass", page_icon="🔴", layout="centered")

# Estilo visual
st.markdown("""
<style>
h1, h2, h3 {
    color: #C10000 !important;
}
.result-box {
    background-color: #ffecec;
    padding: 1em;
    border-left: 5px solid #C10000;
    border-radius: 6px;
    font-size: 1rem;
    white-space: pre-wrap;
    line-height: 1.5;
}
.stButton>button {
    background-color: #C10000;
    color: white;
    font-weight: 500;
    border-radius: 6px;
    padding: 0.4em 1em;
    border: none;
}
.status-box {
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 15px;
    background-color: #ffecec;
    border: 1px solid #C10000;
}
</style>
""", unsafe_allow_html=True)

# Título
st.title("HeatGlass")
st.write("Análise inteligente de ligações: temperatura emocional, impacto no negócio e status do atendimento.")

# Upload de áudio
uploaded_file = st.file_uploader("Envie o áudio da ligação (.mp3)", type=["mp3"])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    st.audio(uploaded_file, format='audio/mp3')

    if st.button("🔍 Analisar Atendimento"):
        # Transcrição via Whisper
        with st.spinner("Transcrevendo o áudio..."):
            with open(tmp_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            transcript_text = transcript.text

        with st.expander("Ver transcrição completa"):
            st.code(transcript_text, language="markdown")

        # Prompt
        prompt = f"""
Você é um especialista em atendimento ao cliente. Avalie a transcrição a seguir:

TRANSCRIÇÃO:
\"\"\"{transcript_text}\"\"\"

Retorne um JSON com os seguintes campos:

{{
  "temperatura": {{"classificacao": "...", "justificativa": "..."}},
  "impacto_comercial": {{"percentual": ..., "faixa": "...", "justificativa": "..."}},
  "status_final": {{"satisfacao": "...", "risco": "...", "desfecho": "..."}},
  "checklist": [
    {{"item": 1, "criterio": "Saudação inicial adequada", "pontos": 10, "resposta": "...", "justificativa": "..."}},
    ...
  ],
  "pontuacao_total": ...,
  "resumo_geral": "..."
}}

Checklist (100 pts totais):
1. Saudação inicial adequada (10 pts)
2. Confirmou histórico do cliente (7 pts)
3. Solicitou dois telefones logo no início (6 pts)
4. Verbalizou o script da LGPD (2 pts)
5. Usou a técnica do eco (5 pts)
6. Escutou com atenção, sem repetições desnecessárias (3 pts)
7. Demonstrou domínio sobre o serviço (5 pts)
8. Consultou o manual antes de pedir ajuda (2 pts)
9. Confirmou corretamente o veículo e ano (5 pts)
10. Perguntou data e motivo do dano (5 pts)
11. Confirmou cidade do cliente (3 pts)
12. Selecionou a primeira loja sugerida (5 pts)
13. Explicou link de acompanhamento (3 pts)
14. Informou prazo de retorno e validade da OS (5 pts)
15. Registrou corretamente no mesmo pedido (5 pts)
16. Tabulação correta com código correspondente (5 pts)
17. Encerramento com todas as orientações finais (10 pts)
18. Informou sobre pesquisa de satisfação (6 pts)

Responda apenas com o JSON e nada mais.
"""

        with st.spinner("Analisando a conversa..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "Você é um analista especializado em atendimento."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3
                )
                result = response.choices[0].message.content.strip()

                if not result.startswith("{"):
                    raise ValueError("Formato de resposta inválido")

                analysis = json.loads(result)

                # Temperatura
                st.subheader("🌡️ Temperatura Emocional")
                temp = analysis.get("temperatura", {})
                temp_class = temp.get("classificacao", "Desconhecida")
                emoji = {'Calma': '😌', 'Neutra': '😐', 'Tensa': '😟', 'Muito Tensa': '😡'}.get(temp_class, '❓')
                st.markdown(f"### {temp_class} {emoji}")
                st.markdown(f"**Justificativa:** {temp.get('justificativa')}")

                # Impacto
                st.subheader("💼 Impacto Comercial")
                impact = analysis.get("impacto_comercial", {})
                pct = float(re.sub(r"[^\d.]", "", str(impact.get("percentual", "0"))))
                st.progress(min(pct / 100, 1.0))
                st.markdown(f"### {int(pct)}% - {impact.get('faixa')}")
                st.markdown(f"**Justificativa:** {impact.get('justificativa')}")

                # Status Final
                st.subheader("📋 Status Final")
                final = analysis.get("status_final", {})
                st.markdown(f"""
                <div class="status-box">
                <strong>Cliente:</strong> {final.get("satisfacao")}<br>
                <strong>Desfecho:</strong> {final.get("desfecho")}<br>
                <strong>Risco:</strong> {final.get("risco")}
                </div>
                """, unsafe_allow_html=True)

                # Checklist
                st.subheader("✅ Checklist Técnico")
                checklist = analysis.get("checklist", [])
                total = float(re.sub(r"[^\d.]", "", str(analysis.get("pontuacao_total", "0"))))
                st.progress(min(total / 100, 1.0))
                st.markdown(f"### {int(total)} pontos de 100")

                with st.expander("Ver Detalhes do Checklist"):
                    for item in checklist:
                        ok = "✅" if item["resposta"].lower() == "sim" else "❌"
                        st.markdown(f"{ok} **{item['item']}. {item['criterio']}** ({item['pontos']} pts) – {item['justificativa']}")

                # Resumo
                st.subheader("📝 Resumo Geral")
                st.markdown(f"<div class='result-box'>{analysis.get('resumo_geral')}</div>", unsafe_allow_html=True)

            except Exception as e:
                st.error("Erro ao processar a análise.")
                st.text_area("Resposta da IA:", value=response.choices[0].message.content.strip(), height=300)
