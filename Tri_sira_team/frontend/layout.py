from dash import html, dcc


def Layout():
    return html.Div(
        children=[
            html.H1(
                children='"Три сыра"',
                style={
                    'textAlign': 'center',
                    'margin': '0',
                    'padding': '20px',
                    'color': 'white',
                    'fontFamily': 'Segoe UI, Arial, sans-serif',
                    'fontSize': '2.5rem',
                    'fontWeight': '300',
                    'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    'borderRadius': '12px 12px 0 0'
                }
            ),
            html.Div(
                children=[
                    html.Div(
                        children=[
                            dcc.Graph(
                                id='map_grid',
                                style={
                                    'height': '100%',
                                    'width': '100%',
                                    'borderRadius': '0 0 0 12px'
                                }
                            )
                        ],
                        style={
                            'flex': '1',
                            'minHeight': '80vh',
                            'padding': '10px',
                            'backgroundColor': '#2c3e50',
                            'borderRadius': '0 0 0 12px',
                            'marginRight': '0',
                            'marginBottom': '20px'
                        }
                    ),
                    html.Div(
                        children=[
                            html.H2(
                                children="Частота получения координат, Гц",
                                style={
                                    'textAlign': 'center',
                                    'margin': '10px 0',
                                    'color': '#ecf0f1',
                                    'fontFamily': 'Segoe UI, Arial, sans-serif',
                                    'fontSize': '1.4rem',
                                    'fontWeight': '400'
                                }
                            ),
                            dcc.Slider(
                                id='frequency_slider',
                                min=0.1,
                                max=10,
                                step=0.1,
                                value=5,
                                marks={i: str(i) for i in [0.1, 1, 2, 5, 10]},
                                tooltip={"placement": "bottom", "always_visible": True}
                            ),
                            html.H2(
                                children="Маршрут",
                                style={
                                    'textAlign': 'center',
                                    'margin': '20px 0 10px 0',
                                    'color': '#ecf0f1',
                                    'fontFamily': 'Segoe UI, Arial, sans-serif',
                                    'fontSize': '1.4rem',
                                    'fontWeight': '400'
                                }
                            ),
                            html.Div(
                                children=[
                                    dcc.Textarea(
                                        id='route',
                                        readOnly=True,
                                        style={
                                            'width': '100%',
                                            'height': '180px',
                                            'flex': '1',
                                            'minHeight': '150px',
                                            'resize': 'none',
                                            'backgroundColor': '#1a252f',
                                            'color': '#ecf0f1',
                                            'border': '1px solid #34495e',
                                            'borderRadius': '8px',
                                            'padding': '12px',
                                            'fontFamily': 'Consolas, Monaco, monospace',
                                            'fontSize': '14px',
                                            'boxSizing': 'border-box',
                                            'display': 'block',
                                            'margin': '0 auto'
                                        }
                                    )
                                ],
                                style={
                                    'display': 'flex',
                                    'justifyContent': 'center',
                                    'alignItems': 'center'
                                }
                            ),
                            html.H2(
                                children="Сохранение маршрута",
                                style={
                                    'textAlign': 'center',
                                    'margin': '20px 0 10px 0',
                                    'color': '#ecf0f1',
                                    'fontFamily': 'Segoe UI, Arial, sans-serif',
                                    'fontSize': '1.4rem',
                                    'fontWeight': '400'
                                }
                            ),
                            html.Div(
                                children=[
                                    dcc.Input(
                                        id='filename',
                                        value='my_path',
                                        style={
                                            'width': 'calc(60% - 8px)',
                                            'padding': '12px',
                                            'marginRight': '10px',
                                            'backgroundColor': '#1a252f',
                                            'color': '#ecf0f1',
                                            'border': '1px solid #34495e',
                                            'borderRadius': '6px',
                                            'fontFamily': 'Segoe UI, Arial, sans-serif',
                                            'fontSize': '14px',
                                            'boxSizing': 'border-box'
                                        }
                                    ),
                                    html.Button(
                                        'Сохранить',
                                        id='save_button',
                                        style={
                                            'width': 'calc(38% - 8px)',
                                            'padding': '12px',
                                            'backgroundColor': '#3498db',
                                            'color': 'white',
                                            'border': 'none',
                                            'borderRadius': '6px',
                                            'cursor': 'pointer',
                                            'fontFamily': 'Segoe UI, Arial, sans-serif',
                                            'fontSize': '14px',
                                            'fontWeight': '500',
                                            'transition': 'all 0.3s ease',
                                            'boxSizing': 'border-box'
                                        }
                                    )
                                ],
                                style={
                                    'display': 'flex',
                                    'justifyContent': 'space-between',
                                    'width': '100%',
                                    'boxSizing': 'border-box'
                                }
                            ),
                            dcc.Interval(
                                id='timer',
                                n_intervals=0
                            )
                        ],
                        style={
                            'width': '320px',
                            'minWidth': '270px',
                            'padding': '20px',
                            'display': 'flex',
                            'flexDirection': 'column',
                            'gap': '15px',
                            'borderLeft': '1px solid #34495e',
                            'backgroundColor': '#2c3e50',
                            'boxSizing': 'border-box',
                            'overflow': 'hidden',
                            'height': 'calc(100vh - 140px)',
                            'marginTop': '10px',
                            'marginBottom': '10px'
                        }
                    )
                ],
                style={
                    'display': 'flex',
                    'flexDirection': 'row',
                    'height': 'calc(100vh - 100px)',
                    'width': '100%',
                    'margin': '0',
                    'padding': '0',
                    'boxSizing': 'border-box',
                    'backgroundColor': '#2c3e50',
                    'borderRadius': '0 0 12px 12px'
                }
            )
        ],
        style={
            'height': '100vh',
            'width': '100%',
            'margin': '0',
            'padding': '20px',
            'boxSizing': 'border-box',
            'overflow': 'hidden',
            'fontFamily': 'Segoe UI, Arial, sans-serif',
            'backgroundColor': '#1a1a2e',
            'background': 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)'
        }
    )
