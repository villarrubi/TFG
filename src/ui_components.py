"""Componentes visuales compartidos para las pantallas Streamlit."""

from textwrap import dedent

import streamlit as st


def aplicar_estilos_base(extra_css: str = "") -> None:
    """Aplica estilos comunes de tarjetas, estados y grids."""
    st.markdown(
        dedent(
            f"""
        <style>
        h1 a, h2 a, h3 a, h4 a, h5 a, h6 a {{
            display: none !important;
        }}
        .ui-grid {{
            display: grid;
            gap: 12px;
            margin: 14px 0 22px;
        }}
        .ui-grid-2 {{
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }}
        .ui-grid-3 {{
            grid-template-columns: repeat(3, minmax(0, 1fr));
        }}
        .ui-grid-4 {{
            grid-template-columns: repeat(4, minmax(0, 1fr));
        }}
        .ui-card {{
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            background: #ffffff;
            padding: 14px 16px;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.07);
        }}
        .ui-label {{
            color: #64748b;
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            margin-bottom: 6px;
        }}
        .ui-value {{
            color: #0f172a;
            font-size: 1.15rem;
            font-weight: 800;
            line-height: 1.25;
        }}
        .ui-note {{
            color: #64748b;
            font-size: 0.86rem;
            margin-top: 8px;
            line-height: 1.35;
        }}
        .ui-pill {{
            display: inline-block;
            border-radius: 999px;
            padding: 5px 10px;
            font-size: 0.78rem;
            font-weight: 700;
        }}
        .ui-ok {{
            border: 1px solid #bbf7d0;
            background: #f0fdf4;
            color: #166534;
        }}
        .ui-warn {{
            border: 1px solid #fed7aa;
            background: #fff7ed;
            color: #9a3412;
        }}
        @media (max-width: 980px) {{
            .ui-grid-4 {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}
        }}
        @media (max-width: 820px) {{
            .ui-grid-2,
            .ui-grid-3 {{
                grid-template-columns: 1fr;
            }}
        }}
        @media (max-width: 620px) {{
            .ui-grid-4 {{
                grid-template-columns: 1fr;
            }}
        }}
        {extra_css}
        </style>
        """
        ).strip(),
        unsafe_allow_html=True,
    )


def render_html(markup: str) -> None:
    """Renderiza HTML quitando la sangría accidental de los bloques multilínea."""
    st.markdown(dedent(markup).strip(), unsafe_allow_html=True)


def estado_badge(ok: bool, texto_ok: str = "Listo", texto_warn: str = "Pendiente") -> str:
    """Devuelve un badge HTML de estado."""
    clase = "ui-ok" if ok else "ui-warn"
    texto = texto_ok if ok else texto_warn
    return f'<span class="ui-pill {clase}">{texto}</span>'
