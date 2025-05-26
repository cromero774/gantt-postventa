import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, State
import sys
import requests
import os
from datetime import datetime
import time

def debug_print(message):
    print(f"DEBUG: {message}", file=sys.stderr)
    sys.stderr.flush()

debug_print("Iniciando aplicaci\u00f3n...")

sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTRvUazuzfWjGl5VWuZJUJslZEf-PpYyHZ_5G2SXwPtu16R71mPSKVQTYjen9UBwQ/pub?gid=865145678&single=true&output=csv"

def cargar_datos():
    debug_print(f"Cargando datos a las {datetime.now().strftime('%H:%M:%S')}")
    try:
        response = requests.get(sheet_url, timeout=15)
        response.raise_for_status()
        df = pd.read_csv(sheet_url)
        df.columns = df.columns.str.strip()
        df['RN'] = df['RN'].astype(str).str.replace(r'[\xa0\s]+', ' ', regex=True).str.strip()

        for col in ['Inicio', 'Fin']:
            df[col] = pd.to_datetime(df[col], format='%m/%d/%Y', errors='coerce')
        df = df.dropna(subset=['Inicio', 'Fin'])

        if df.empty:
            sample_dates = pd.date_range(start='2023-01-01', periods=3)
            df = pd.DataFrame({
                'RN': ['Ejemplo 1', 'Ejemplo 2', 'Ejemplo 3'],
                'Estado': ['En desarrollo', 'Entregado', 'Backlog'],
                'Inicio': sample_dates,
                'Fin': sample_dates + pd.Timedelta(days=30)
            })

        df['Inicio_str'] = df['Inicio'].dt.strftime('%Y-%m-%d')
        df['Fin_str'] = df['Fin'].dt.strftime('%Y-%m-%d')
        df['Duracion'] = (df['Fin'] - df['Inicio']).dt.days
        df['Mes'] = df['Fin'].dt.to_period('M').astype(str)

        return df, True

    except Exception as e:
        debug_print(f"Error al cargar datos: {str(e)}")
        sample_dates = pd.date_range(start='2023-01-01', periods=3)
        df = pd.DataFrame({
            'RN': ['Error - Sin datos', 'Ejemplo 2', 'Ejemplo 3'],
            'Estado': ['Error', 'Error', 'Error'],
            'Inicio': sample_dates,
            'Fin': sample_dates + pd.Timedelta(days=30),
            'Inicio_str': sample_dates.strftime('%Y-%m-%d'),
            'Fin_str': (sample_dates + pd.Timedelta(days=30)).strftime('%Y-%m-%d'),
            'Duracion': [30, 30, 30],
            'Mes': sample_dates.strftime('%Y-%m')
        })
        return df, False

df, carga_exitosa = cargar_datos()

color_estado = {
    'Entregado': '#2ecc71',
    'En desarrollo': '#1abc9c',
    'Backlog': '#f1c40f',
    'Para refinar': '#f5d76e',
    'Escribiendo': '#e67e22',
    'Para escribir': '#e74c3c',
    'En An\u00e1lisis': '#9b59b6',
    'Cancelado': '#95a5a6',
    'Error': '#e74c3c'
}

app = Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H1("Gantt Desarrollo Postventa", style={'textAlign': 'center', 'margin': '20px 0'}),
    html.Div([
        html.Div([
            html.Label("Mes de entrega:"),
            dcc.Dropdown(
                id='mes-dropdown',
                options=[{'label': 'Todos', 'value': 'Todos'}] +
                        [{'label': mes, 'value': mes} for mes in sorted(df['Mes'].unique())],
                value='Todos',
                clearable=False
            )
        ], style={'width': '32%', 'display': 'inline-block'}),
        html.Div([
            html.Label("Estado:"),
            dcc.Dropdown(
                id='estado-dropdown',
                options=[{'label': 'Todos', 'value': 'Todos'}] +
                        [{'label': estado, 'value': estado} for estado in sorted(df['Estado'].unique())],
                value='Todos',
                clearable=False
            )
        ], style={'width': '32%', 'display': 'inline-block', 'marginLeft': '10px'}),
        html.Div([
            html.Button('Actualizar datos', id='refresh-button',
                        style={'marginTop': '20px', 'padding': '8px 16px', 'backgroundColor': '#3498db',
                               'color': 'white', 'border': 'none', 'borderRadius': '4px', 'cursor': 'pointer'}),
            html.Div(id='last-update-time',
                     children=f"\u00daltima actualizaci\u00f3n: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    style={'marginTop': '5px', 'fontSize': '12px'})
        ], style={'width': '32%', 'display': 'inline-block', 'marginLeft': '10px', 'textAlign': 'center'})
    ], style={'marginBottom': '20px'}),
    html.Div([
        html.Label("Tema:"),
        dcc.RadioItems(
            id='theme-switch',
            options=[
                {'label': 'Claro', 'value': 'light'},
                {'label': 'Oscuro', 'value': 'dark'}
            ],
            value='light',
            labelStyle={'display': 'inline-block', 'marginRight': '15px'}
        ),
    ], style={'marginBottom': '20px'}),
    dcc.Interval(id='interval-component', interval=60*1000, n_intervals=0),
    dcc.Store(id='stored-data'),
    html.Div([
        dcc.Graph(id='gantt-graph', responsive=True, style={'height': '100%', 'width': '100%'})
    ], style={'height': '80vh', 'overflowY': 'auto', 'width': '100%'})
])

@app.callback(
    [Output('stored-data', 'data'),
     Output('mes-dropdown', 'options'),
     Output('estado-dropdown', 'options'),
     Output('last-update-time', 'children')],
    [Input('refresh-button', 'n_clicks'),
     Input('interval-component', 'n_intervals')],
    [State('mes-dropdown', 'value'),
     State('estado-dropdown', 'value')]
)
def actualizar_datos(n_clicks, n_intervals, mes_actual, estado_actual):
    df_actualizado, _ = cargar_datos()
    opciones_mes = [{'label': 'Todos', 'value': 'Todos'}] + [
        {'label': mes, 'value': mes} for mes in sorted(df_actualizado['Mes'].unique())
    ]
    opciones_estado = [{'label': 'Todos', 'value': 'Todos'}] + [
        {'label': estado, 'value': estado} for estado in sorted(df_actualizado['Estado'].unique())
    ]
    tiempo_actualizacion = f"\u00daltima actualizaci\u00f3n: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    return df_actualizado.to_dict('records'), opciones_mes, opciones_estado, tiempo_actualizacion

@app.callback(
    Output('gantt-graph', 'figure'),
    [Input('stored-data', 'data'),
     Input('mes-dropdown', 'value'),
     Input('estado-dropdown', 'value'),
     Input('theme-switch', 'value')]
)
def actualizar_grafico(data, mes, estado, theme):
    if not data:
        df_filtrado = df.copy()
    else:
        df_filtrado = pd.DataFrame(data)
        for col in ['Inicio', 'Fin']:
            if col in df_filtrado.columns:
                df_filtrado[col] = pd.to_datetime(df_filtrado[col])

    if mes != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Mes'] == mes]
    if estado != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Estado'] == estado]

    if df_filtrado.empty:
        return px.scatter(title="Sin datos con los filtros seleccionados")

    if theme == 'dark':
        plot_bgcolor = '#23272f'
        paper_bgcolor = '#23272f'
        font_color = '#f0f0f0'
        gridcolor = '#444'
    else:
        plot_bgcolor = 'white'
        paper_bgcolor = 'white'
        font_color = '#222'
        gridcolor = '#eee'

    df_filtrado = df_filtrado.sort_values('Inicio', ascending=True)
    df_filtrado['RN'] = pd.Categorical(df_filtrado['RN'], categories=df_filtrado['RN'].unique(), ordered=True)

    today = pd.Timestamp.now().normalize()
    df_filtrado['Dias_restantes'] = (df_filtrado['Fin'] - today).dt.days.clip(lower=0)

    fig = px.timeline(
        df_filtrado,
        x_start="Inicio",
        x_end="Fin",
        y="RN",
        color="Estado",
        color_discrete_map=color_estado,
        custom_data=["RN", "Inicio_str", "Fin_str", "Duracion", "Dias_restantes"],
        labels={'Estado': 'Estado', 'RN': 'Requerimiento'},
        title=f"Postventa - {estado if estado != 'Todos' else 'Todos los estados'} | {mes if mes != 'Todos' else 'Todos los meses'}"
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Inicio de desarrollo: %{customdata[1]}<br>"
            "Fin de desarrollo OK QA: %{customdata[2]}<br>"
            "Duraci\u00f3n: %{customdata[3]} d\u00edas<br>"
            "D\u00edas restantes: %{customdata[4]} d\u00edas"
        ),
        text="",
        marker=dict(line=dict(width=0.3, color='DarkSlateGrey'))
    )

    rows_count = len(df_filtrado)
    row_height = 25
    min_height = 400
    max_height = 1200
    dynamic_height = row_height * rows_count
    graph_height = max(min_height, min(dynamic_height, max_height))

    fig.update_layout(
        height=graph_height,
        xaxis=dict(title="Fecha", tickformat="%Y-%m-%d", gridcolor=gridcolor),
        yaxis=dict(autorange="reversed"),
        legend=dict(title="Estado", orientation="v", yanchor="top", y=1, xanchor="left", x=1.01),
        plot_bgcolor=plot_bgcolor,
        paper_bgcolor=paper_bgcolor,
        font=dict(color=font_color),
        margin=dict(l=180, r=200, t=80, b=20),
        bargap=0.15,
        shapes=[
            dict(
                type='line', x0=today, y0=0, x1=today, y1=rows_count,
                line=dict(color='red', width=2, dash='dash')
            )
        ],
        annotations=[
            dict(
                x=today, y=0.5, xref='x', yref='y',
                text=f'Hoy: {today.strftime("%Y-%m-%d")}',
                showarrow=True, arrowhead=7, ax=0, ay=-40,
                font=dict(color='red', size=12),
                bgcolor='white' if theme == 'light' else '#23272f',
                bordercolor='red', borderwidth=1, opacity=0.9
            )
        ]
    )

    return fig

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug_print("Iniciando servidor...")
    app.run(host='0.0.0.0', port=port, debug=False)































