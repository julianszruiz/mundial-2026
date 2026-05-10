import streamlit as st
import json, os
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from data import TEAMS, ALL_STICKERS, SPECIAL_STICKERS, TEAM_BY_CODE

# ── Configuración de página ───────────────────────────────────────────────────
st.set_page_config(
    page_title="⚽ Mi Álbum Mundial 2026",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Persistencia: Supabase en la nube, JSON local como fallback ───────────────
CFILE = "collection.json"

@st.cache_resource
def get_supabase():
    """Devuelve el cliente de Supabase si hay credenciales, o None."""
    try:
        from supabase import create_client
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception:
        return None

def load_col() -> dict:
    sb = get_supabase()
    if sb is not None:
        result = sb.table("collection").select("sticker_id,count").execute()
        return {r["sticker_id"]: r["count"] for r in result.data}
    # Fallback local
    if os.path.exists(CFILE):
        with open(CFILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_col(col: dict):
    sb = get_supabase()
    if sb is not None:
        to_upsert = [{"sticker_id": k, "count": v} for k, v in col.items() if v > 0]
        to_delete  = [k for k, v in col.items() if v == 0]
        if to_upsert:
            sb.table("collection").upsert(to_upsert, on_conflict="sticker_id").execute()
        for i in range(0, len(to_delete), 100):
            sb.table("collection").delete().in_("sticker_id", to_delete[i:i+100]).execute()
    else:
        with open(CFILE, "w", encoding="utf-8") as f:
            json.dump(col, f, indent=2, ensure_ascii=False)

if "col" not in st.session_state:
    st.session_state.col = load_col()

col = st.session_state.col

def on_change_count(sid: str):
    val = st.session_state.get(f"n_{sid}", 0)
    st.session_state.col[sid] = int(val)
    save_col(st.session_state.col)

# ── CSS global (solo para elementos nativos de Streamlit) ─────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
[data-testid="metric-container"] {
    background: #f8f9fa; border-radius: 12px; padding: 16px; border: 1px solid #e0e0e0;
}
/* Ocultar label del number_input */
div[data-testid="stNumberInput"] label { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
POS_LABEL = {
    "POR": "Portero", "DEF": "Defensa", "MED": "Mediocampista",
    "DEL": "Delantero", "LOG": "Escudo", "FOT": "Foto equipo", "ESP": "Especial",
}

def flag_url(code: str) -> str:
    return f"https://flagcdn.com/20x15/{code}.png"

# ── Tarjeta de ficha (100% estilos inline para garantizar el render) ──────────
def render_sticker_card(s: dict) -> str:
    sid  = s["id"]
    cnt  = col.get(sid, 0)
    pos  = s["pos"]
    team = TEAM_BY_CODE.get(s["team"])
    name = s["name"]

    # ── Colores según estado ──
    if s["foil"]:
        bg     = "linear-gradient(135deg,#f6d365 0%,#fda085 100%)"
        border = "#f6a623"
        txt    = "#333333"
        av_bg  = "rgba(0,0,0,0.12)"
    elif s["photo"]:
        bg     = "linear-gradient(135deg,#667eea 0%,#764ba2 100%)"
        border = "#764ba2"
        txt    = "white"
        av_bg  = "rgba(255,255,255,0.20)"
    elif cnt == 0:
        bg     = "#f0f0f0"
        border = "#cccccc"
        txt    = "#aaaaaa"
        av_bg  = "#dedede"
    elif cnt == 1:
        tc     = team["color"] if team else "#2ecc71"
        bg     = f"linear-gradient(135deg,{tc}bb 0%,{tc} 100%)"
        border = tc
        txt    = "white"
        av_bg  = "rgba(255,255,255,0.25)"
    else:
        bg     = "linear-gradient(135deg,#f39c12 0%,#e67e22 100%)"
        border = "#e67e22"
        txt    = "white"
        av_bg  = "rgba(255,255,255,0.25)"

    # ── Avatar con iniciales ──
    words = name.split()
    if pos == "LOG":
        av, av_fs = "🏅", "1.4rem"
    elif pos == "FOT":
        av, av_fs = "📸", "1.4rem"
    elif pos == "ESP":
        av, av_fs = "⭐", "1.4rem"
    else:
        av = (words[0][0] + (words[-1][0] if len(words) > 1 else "")).upper()
        av_fs = "0.9rem" if len(av) <= 2 else "1.1rem"

    # ── Bandera ──
    flag_img = (
        f'<img src="{flag_url(team["flag"])}" '
        f'style="height:13px;margin-bottom:3px;border-radius:2px">'
    ) if team else ""

    # ── Badge repetida ──
    badge = (
        f'<div style="position:absolute;top:5px;right:5px;background:#c0392b;'
        f'color:white;border-radius:50%;width:20px;height:20px;font-size:0.55rem;'
        f'font-weight:700;display:flex;align-items:center;justify-content:center;">×{cnt}</div>'
    ) if cnt > 1 else ""

    pos_lbl = POS_LABEL.get(pos, pos)

    return f"""
<div style="
    background:{bg};
    border:2px solid {border};
    border-radius:12px;
    padding:10px 6px 8px 6px;
    text-align:center;
    min-height:135px;
    display:flex;
    flex-direction:column;
    align-items:center;
    justify-content:center;
    position:relative;
    font-family:'Helvetica Neue',Arial,sans-serif;
    gap:3px;
    box-sizing:border-box;
">
  {badge}
  <span style="font-size:0.55rem;font-weight:700;color:{txt};opacity:0.70;letter-spacing:1px;">{sid}</span>
  {flag_img}
  <div style="
      width:50px;height:50px;border-radius:50%;
      background:{av_bg};
      display:flex;align-items:center;justify-content:center;
      font-size:{av_fs};font-weight:800;color:{txt};
      border:2px solid rgba(255,255,255,0.40);
      margin:2px 0;
  ">{av}</div>
  <span style="
      font-size:0.63rem;font-weight:600;color:{txt};
      max-width:92px;overflow:hidden;text-overflow:ellipsis;
      white-space:nowrap;display:block;line-height:1.3;
  ">{name[:20]}</span>
  <span style="
      font-size:0.52rem;color:{txt};opacity:0.85;
      background:rgba(0,0,0,0.13);border-radius:4px;padding:1px 6px;margin-top:1px;
  ">{pos_lbl}</span>
</div>
"""

# ── Stats globales ────────────────────────────────────────────────────────────
total   = len(ALL_STICKERS)
tengo   = sum(1 for s in ALL_STICKERS if col.get(s["id"], 0) >= 1)
reps_n  = sum(col.get(s["id"], 0) - 1 for s in ALL_STICKERS if col.get(s["id"], 0) > 1)
faltan  = total - tengo
pct     = round(tengo / total * 100, 1) if total else 0

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏆 Mundial 2026")
    st.markdown(f"**{pct}%** completado")
    st.progress(tengo / total if total else 0)
    st.markdown("---")
    page = st.radio("Navegar", ["🏠 Inicio", "📖 Álbum", "🔄 Repetidas", "❓ Faltan"],
                    label_visibility="collapsed")
    st.markdown("---")
    st.caption("Panini FIFA World Cup 2026™\n980 fichas · 48 selecciones")

# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA: INICIO
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Inicio":
    st.title("🏆 Mi Álbum Panini · Mundial 2026")
    st.markdown("Marcá las fichas que tenés, descubrí cuáles te faltan y organizá tus repetidas para intercambiar.")
    st.markdown("---")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📦 Total fichas", total)
    c2.metric("✅ Tengo", tengo, delta=f"{pct}%")
    c3.metric("❓ Faltan", faltan)
    c4.metric("🔄 Repetidas", reps_n)

    st.markdown("---")
    col_donut, col_bars = st.columns([1, 2])

    with col_donut:
        st.subheader("Completitud general")
        fig = go.Figure(go.Pie(
            values=[tengo, faltan],
            labels=["Tengo", "Faltan"],
            hole=0.65,
            marker_colors=["#2ecc71", "#e0e0e0"],
            textinfo="none",
        ))
        fig.add_annotation(text=f"<b>{pct}%</b>", x=0.5, y=0.5, font_size=24, showarrow=False)
        fig.update_layout(showlegend=True, margin=dict(t=10, b=10, l=10, r=10),
                          height=280, legend=dict(orientation="h", y=-0.1))
        st.plotly_chart(fig, use_container_width=True)

    with col_bars:
        st.subheader("Progreso por selección")
        rows = []
        for t in TEAMS:
            tids   = [s["id"] for s in t["stickers"]]
            t_have = sum(1 for sid in tids if col.get(sid, 0) >= 1)
            rows.append({"Selección": t["name"], "%": round(t_have / len(tids) * 100, 1)})
        df_prog = pd.DataFrame(rows).sort_values("%", ascending=False)
        fig2 = px.bar(df_prog, x="%", y="Selección", orientation="h",
                      text="%", color="%",
                      color_continuous_scale=["#ff6b6b", "#ffd93d", "#6bcb77"],
                      range_color=[0, 100], height=900)
        fig2.update_traces(texttemplate="%{text:.0f}%", textposition="outside")
        fig2.update_layout(margin=dict(l=10, r=10, t=10, b=10),
                           yaxis=dict(autorange="reversed"),
                           coloraxis_showscale=False, xaxis_range=[0, 115])
        st.plotly_chart(fig2, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA: ÁLBUM
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📖 Álbum":
    st.title("📖 Álbum de Fichas")

    team_names = ["⭐ Fichas Especiales (FWC)"] + [t["name"] for t in TEAMS]
    sel = st.selectbox("Seleccioná una selección:", team_names)

    if sel == "⭐ Fichas Especiales (FWC)":
        stickers_show = SPECIAL_STICKERS
        st.markdown("**Fichas introductorias**: logo, emblemas, mascota, historia del mundial.")
    else:
        team = next(t for t in TEAMS if t["name"] == sel)
        stickers_show = team["stickers"]
        t_have = sum(1 for s in stickers_show if col.get(s["id"], 0) >= 1)
        st.markdown(
            f'<img src="{flag_url(team["flag"])}" style="height:22px;vertical-align:middle;margin-right:6px">'
            f'<b>{team["name"]}</b> — {t_have} / {len(stickers_show)} fichas',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Leyenda de estados
    st.html("""
<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:8px;font-family:sans-serif;font-size:0.72rem;">
  <span><span style="display:inline-block;width:12px;height:12px;border-radius:3px;background:#f0f0f0;border:1px solid #ccc;margin-right:4px"></span>No tengo</span>
  <span><span style="display:inline-block;width:12px;height:12px;border-radius:3px;background:#2ecc71;margin-right:4px"></span>Tengo (1)</span>
  <span><span style="display:inline-block;width:12px;height:12px;border-radius:3px;background:#e67e22;margin-right:4px"></span>Repetida (2+)</span>
  <span><span style="display:inline-block;width:12px;height:12px;border-radius:3px;background:linear-gradient(135deg,#f6d365,#fda085);margin-right:4px"></span>FOIL ✨</span>
</div>
""")

    ba1, ba2, _ = st.columns([1, 1, 4])
    if ba1.button("✅ Marcar todas como tenidas"):
        for s in stickers_show:
            if st.session_state.col.get(s["id"], 0) == 0:
                st.session_state.col[s["id"]] = 1
        save_col(st.session_state.col)
        st.rerun()
    if ba2.button("🗑️ Limpiar selección"):
        for s in stickers_show:
            st.session_state.col.pop(s["id"], None)
        save_col(st.session_state.col)
        st.rerun()

    st.markdown("")

    # Grid de 5 columnas — usamos st.html() para las tarjetas
    COLS = 5
    for row_start in range(0, len(stickers_show), COLS):
        row_items = stickers_show[row_start: row_start + COLS]
        cols_ui = st.columns(COLS)
        for j, s in enumerate(row_items):
            sid = s["id"]
            with cols_ui[j]:
                # ← Aquí estaba el bug: ahora usamos st.html()
                st.html(render_sticker_card(s))
                st.number_input(
                    sid,
                    min_value=0, max_value=20,
                    value=int(col.get(sid, 0)),
                    key=f"n_{sid}",
                    label_visibility="collapsed",
                    on_change=on_change_count,
                    args=(sid,),
                )

# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA: REPETIDAS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔄 Repetidas":
    st.title("🔄 Fichas Repetidas")

    reps = [s for s in ALL_STICKERS if col.get(s["id"], 0) > 1]
    total_extra = sum(col.get(s["id"], 0) - 1 for s in reps)

    if not reps:
        st.info("No tenés fichas repetidas todavía. ¡Seguí abriendo sobres!")
    else:
        st.markdown(f"**{len(reps)} fichas con repetición** · **{total_extra} copias extra** para intercambio.")
        st.markdown("---")

        rows = []
        for s in sorted(reps, key=lambda x: (x["team"], x["id"])):
            team = TEAM_BY_CODE.get(s["team"])
            rows.append({
                "Ficha": s["id"],
                "Jugador / Contenido": s["name"],
                "Selección": team["name"] if team else "Especial",
                "Posición": POS_LABEL.get(s["pos"], s["pos"]),
                "Copias totales": col.get(s["id"], 0),
                "Copias extra 🔄": col.get(s["id"], 0) - 1,
            })
        df_reps = pd.DataFrame(rows)

        equipos_reps = ["Todos"] + sorted(df_reps["Selección"].unique().tolist())
        fil = st.selectbox("Filtrar por selección:", equipos_reps)
        if fil != "Todos":
            df_reps = df_reps[df_reps["Selección"] == fil]

        st.dataframe(df_reps, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("📋 Lista para intercambio")
        lines = [f"{r['Ficha']} — {r['Jugador / Contenido']} ({r['Selección']}) ×{r['Copias extra 🔄']}"
                 for _, r in df_reps.iterrows()]
        st.text_area("Copiá y pegá esta lista:", "\n".join(lines), height=200)

# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA: FALTAN
# ══════════════════════════════════════════════════════════════════════════════
elif page == "❓ Faltan":
    st.title("❓ Fichas que Faltan")

    missing = [s for s in ALL_STICKERS if col.get(s["id"], 0) == 0]

    if not missing:
        st.success("🎉 ¡Álbum completo! ¡Felicitaciones!")
    else:
        st.markdown(f"**{len(missing)} fichas pendientes** de {total} totales.")
        st.markdown("---")

        rows = []
        for s in missing:
            team = TEAM_BY_CODE.get(s["team"])
            rows.append({
                "Ficha": s["id"],
                "Jugador / Contenido": s["name"],
                "Selección": team["name"] if team else "Especial",
                "Posición": POS_LABEL.get(s["pos"], s["pos"]),
                "FOIL": "⭐" if s["foil"] else "",
            })
        df_miss = pd.DataFrame(rows)

        c_fil1, c_fil2 = st.columns([2, 1])
        equipos_miss = ["Todos"] + sorted(df_miss["Selección"].unique().tolist())
        fil2 = c_fil1.selectbox("Filtrar por selección:", equipos_miss)
        solo_foil = c_fil2.checkbox("Solo FOIL ⭐")

        if fil2 != "Todos":
            df_miss = df_miss[df_miss["Selección"] == fil2]
        if solo_foil:
            df_miss = df_miss[df_miss["FOIL"] == "⭐"]

        for equipo in sorted(df_miss["Selección"].unique()):
            sub = df_miss[df_miss["Selección"] == equipo]
            with st.expander(f"🏳️ {equipo} — faltan {len(sub)}", expanded=False):
                st.dataframe(sub.drop(columns=["Selección"]),
                             use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("📋 Lista para buscar")
        lines2 = [f"{r['Ficha']} — {r['Jugador / Contenido']} ({r['Selección']})"
                  for _, r in df_miss.iterrows()]
        st.text_area("Fichas faltantes:", "\n".join(lines2), height=250)
