import random
from collections import deque
from dash import Output, Input, State
import plotly.express as px
import plotly.graph_objs as go

MILLISECONDS_COEFFICIENT = 1000

path_queue = deque(maxlen=5)


def register_callbacks(app):
    @app.callback(
        Output(component_id='map_grid', component_property='figure'),
        Input(component_id='timer', component_property='n_intervals'))
    def draw_map(n):
        global path_queue

        x = random.randint(3, 10)
        y = random.randint(3, 10)

        path_queue.append((x, y))

        fig = px.scatter(
            app.beacons,
            x="X",
            y="Y",
            text="Name",
            color="Name",
            symbol="Name",
            size_max=15
        )

        fig.update_traces(
            marker=dict(
                size=12,
                line=dict(width=2, color='black')
            ),
            textposition='top center',
            hovertemplate=(
                    "<b>📡 Маяк</b><br>" +
                    "<b>Название:</b> %{text}<br>" +
                    "<b>Координата X:</b> %{x}<br>" +
                    "<b>Координата Y:</b> %{y}<br>" +
                    "<extra></extra>"
            )
        )

        for i, beacon in app.beacons.iterrows():
            fig.add_trace(go.Scatter(
                x=[beacon["X"]],
                y=[beacon["Y"]],
                mode='markers',
                marker=dict(
                    size=25,
                    color=px.colors.qualitative.Set1[i % len(px.colors.qualitative.Set1)],
                    symbol='circle',
                    opacity=0.2,
                    line=dict(width=0)
                ),
                showlegend=False,
                hoverinfo='skip'
            ))

        if len(path_queue) > 1:
            path_x = [point[0] for point in path_queue]
            path_y = [point[1] for point in path_queue]

            fig.add_trace(go.Scatter(
                x=path_x,
                y=path_y,
                mode='lines',
                line=dict(
                    color='rgba(200, 200, 200, 0.3)',
                    width=1,
                    dash='dot'
                ),
                name='Пройденный путь',
                showlegend=False,
                hoverinfo='skip'
            ))

            if len(path_queue) > 1:
                path_points_x = path_x[:-1]
                path_points_y = path_y[:-1]

                footprint_emoji = '🐾'

                for i, (pwx, pwy) in enumerate(zip(path_points_x, path_points_y)):
                    emoji = footprint_emoji

                    fig.add_trace(go.Scatter(
                        x=[pwx],
                        y=[pwy],
                        mode='text+markers',
                        text=[emoji],
                        textfont=dict(
                            size=20,
                            color='rgba(180, 180, 180, 0.8)'
                        ),
                        marker=dict(
                            size=0,
                            opacity=0
                        ),
                        showlegend=False,
                        hovertemplate=(
                                "<b>🐾 След</b><br>" +
                                "<b>Порядок:</b> {} из {}<br>".format(i + 1, len(path_points_x)) +
                                "<b>Координата X:</b> {}<br>".format(pwx) +
                                "<b>Координата Y:</b> {}<br>".format(pwy) +
                                "<extra></extra>"
                        ),
                        name=f'След {i + 1}'
                    ))

        fig.add_trace(go.Scatter(
            x=[x],
            y=[y],
            mode='markers',
            marker=dict(
                size=35,
                color='gold',
                symbol='circle',
                opacity=0.3,
                line=dict(width=0)
            ),
            showlegend=False,
            hoverinfo='skip'
        ))

        fig.add_trace(go.Scatter(
            x=[x],
            y=[y],
            mode='markers+text',
            marker=dict(
                size=20,
                color='gold',
                symbol='star',
                line=dict(width=3, color='yellow')
            ),
            text=["ВЫ"],
            textposition='top center',
            name='Это Вы!',
            hovertemplate=(
                    "<b>👤 Ваша позиция</b><br>" +
                    "<b>Координата X:</b> %{x}<br>" +
                    "<b>Координата Y:</b> %{y}<br>" +
                    "<extra></extra>"
            )
        ))

        fig.update_layout(
            title=dict(
                text="🗺️ Карта маяков с идентификацией",
                x=0.5,
                font=dict(
                    size=24,
                    color='white',
                    family='Segoe UI, Arial, sans-serif'
                )
            ),
            xaxis_title="X координата",
            yaxis_title="Y координата",
            legend_title=dict(
                text="📡 Маяки",
                font=dict(
                    size=16,
                    color='#ecf0f1',
                    family='Segoe UI, Arial, sans-serif'
                )
            ),
            xaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(100, 100, 100, 0.3)',
                zeroline=True,
                zerolinewidth=2,
                zerolinecolor='rgba(200, 200, 200, 0.5)',
                showline=True,
                linewidth=2,
                linecolor='rgba(200, 200, 200, 0.5)',
                tickfont=dict(
                    size=13,
                    color='#bdc3c7',
                    family='Segoe UI, Arial, sans-serif'
                ),
                title_font=dict(
                    size=16,
                    color='#ecf0f1',
                    family='Segoe UI, Arial, sans-serif'
                )
            ),
            yaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(100, 100, 100, 0.3)',
                zeroline=True,
                zerolinewidth=2,
                zerolinecolor='rgba(200, 200, 200, 0.5)',
                showline=True,
                linewidth=2,
                linecolor='rgba(200, 200, 200, 0.5)',
                tickfont=dict(
                    size=13,
                    color='#bdc3c7',
                    family='Segoe UI, Arial, sans-serif'
                ),
                title_font=dict(
                    size=16,
                    color='#ecf0f1',
                    family='Segoe UI, Arial, sans-serif'
                )
            ),
            plot_bgcolor='rgba(30, 30, 30, 0.9)',
            paper_bgcolor='rgba(40, 40, 40, 1)',
            font=dict(
                family='Segoe UI, Arial, sans-serif',
                color='white',
                size=14
            ),
            legend=dict(
                font=dict(
                    size=12,
                    color='#ecf0f1',
                    family='Segoe UI, Arial, sans-serif'
                ),
                bgcolor='rgba(30, 30, 30, 0.7)',
                bordercolor='rgba(200, 200, 200, 0.3)',
                borderwidth=1,
                itemclick=False,
                itemdoubleclick=False,
            ),
            margin=dict(l=60, r=60, t=80, b=60)
        )

        return fig

    @app.callback(
        Output(component_id='timer', component_property='interval'),
        Input(component_id='frequency_slider', component_property='value'))
    def change_frequency(frequency):
        return 1 / frequency * MILLISECONDS_COEFFICIENT

    @app.callback(
        Output(component_id='route', component_property='value'),
        Input(component_id='timer', component_property='n_intervals'),
        State(component_id='route', component_property='value'))
    def update_route(n, current_text):
        if path_queue:
            x, y = path_queue[-1]

            new_entry = f"X: {x}, Y: {y}\n"

            if current_text:
                updated_text = current_text + new_entry
            else:
                updated_text = new_entry

            return updated_text

        return current_text

    @app.callback(
        Input(component_id='save_button', component_property='n_clicks'))
    def save_route(n):
        pass
