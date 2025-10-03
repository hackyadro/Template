import streamlit as st
import json
import time
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
import paho.mqtt.client as mqtt
import threading
import os

st.set_page_config(
    page_title="Indoor Navigation",
    page_icon="^_~",
    layout="wide"
)

class MQTTWebSocketClient:
    def __init__(self):
        self.client = mqtt.Client(client_id="FrontendWS", transport="websockets")
        self.current_position = {"x": 2.5, "y": 2.5}
        self.detected_beacons = []  # Все обнаруженные маяки в реальном времени
        self.positioning_beacons = []  # Маяки, использованные для позиционирования
        self.positions_history = []
        self.connected = False
        self.beacon_config = {}
        
    # def load_beacon_config(self):
    #     """Загружает конфигурацию всех маяков из файла"""
    #     beacons = {}
    #     try:
    #         beacons_file = "/app/data/standart.beacons"
    #         if os.path.exists(beacons_file):
    #             with open(beacons_file, 'r') as f:
    #                 lines = f.readlines()
    #                 for line in lines[1:]:
    #                     if line.strip():
    #                         name, x, y = line.strip().split(';')
    #                         beacons[name] = {
    #                             'x': float(x),
    #                             'y': float(y),
    #                             'name': name
    #                         }
    #             print(f"Loaded {len(beacons)} beacons from configuration")
    #     except Exception as e:
    #         print(f"Error loading beacon config: {e}")
    #     return beacons
    
    def publish_beacon_config(self, beacons_dict):
        try:
            beacon_data = {
                "beacons": beacons_dict,
                "timestamp": time.time(),
                "type": "full_config"
            }
            self.client.publish("beacons/management/setConf", json.dumps(beacon_data))
            print(f"✅ Beacon configuration published with {len(beacons_dict)} beacons")
            return True
        except Exception as e:
            print(f"Failed to publish beacon configuration: {e}")
            return False

        
    def on_connect(self, client, userdata, flags, rc):
        self.connected = True
        st.success("Connected to MQTT via WebSocket")
        client.subscribe("navigation/position/current")
        client.subscribe("ble/beacons/raw")
        
    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            
            if msg.topic == "navigation/position/current":
                self.current_position = {
                    "x": payload['x'],
                    "y": payload['y'],
                    "timestamp": payload.get('timestamp', time.time())
                }
                self.positioning_beacons = payload.get('used_beacons', [])
                
                # Сохраняем историю позиций
                self.positions_history.append({
                    'x': self.current_position['x'],
                    'y': self.current_position['y'],
                    'timestamp': self.current_position['timestamp']
                })
                
                # Ограничиваем размер истории
                if len(self.positions_history) > 50:
                    self.positions_history.pop(0)
                    
            elif msg.topic == "ble/beacons/raw":
                self.detected_beacons = payload.get('beacons', [])
                
        except json.JSONDecodeError as e:
            st.error(f"JSON decode error: {e}")
            
    def start(self):
        try:
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.connect("mqtt-broker", 9001, 60)
            threading.Thread(target=self.client.loop_forever, daemon=True).start()
        except Exception as e:
            st.error(f"WebSocket connection error: {e}")

def create_navigation_map(current_pos, beacon_config, positioning_beacons, history):
    """Создает карту навигации с различными типами маяков"""
    fig = go.Figure()
    
    # Определяем границы карты
    if beacon_config:
        x_coords = [beacon['x'] for beacon in beacon_config.values()]
        y_coords = [beacon['y'] for beacon in beacon_config.values()]
        x_min, x_max = min(x_coords) - 1, max(x_coords) + 1
        y_min, y_max = min(y_coords) - 1, max(y_coords) + 1
    else:
        x_min, x_max, y_min, y_max = -1, 6, -1, 6
    
    # Добавляем сетку помещения
    fig.add_shape(
        type="rect", 
        x0=x_min, y0=y_min, x1=x_max, y1=y_max, 
        line=dict(color="black", width=2), 
        fillcolor="lightgray", 
        opacity=0.1
    )
    
    # 1. ВСЕ маяки из конфигурации (серые)
    if beacon_config:
        beacon_list = list(beacon_config.values())
        fig.add_trace(go.Scatter(
            x=[b["x"] for b in beacon_list],
            y=[b["y"] for b in beacon_list],
            mode='markers+text',
            name='Available Beacons',
            marker=dict(
                size=12, 
                color='lightgray', 
                symbol='square',
                line=dict(width=1, color='darkgray')
            ),
            text=[b["name"] for b in beacon_list],
            textposition="top center",
            hovertemplate="<b>%{text}</b><br>Position: (%{x}, %{y})<extra></extra>"
        ))
    
    # 2. Маяки, использованные для позиционирования (красные)
    if positioning_beacons:
        # Обогащаем данные маяков для позиционирования информацией из конфигурации
        enriched_positioning_beacons = []
        for beacon in positioning_beacons:
            beacon_name = beacon.get('name')
            if beacon_name in beacon_config:
                config_data = beacon_config[beacon_name]
                enriched_beacon = {
                    'x': config_data['x'],
                    'y': config_data['y'],
                    'name': beacon_name,
                    'distance': beacon.get('distance', 0),
                    'rssi': beacon.get('rssi', 'N/A')
                }
                enriched_positioning_beacons.append(enriched_beacon)
        
        if enriched_positioning_beacons:
            fig.add_trace(go.Scatter(
                x=[b["x"] for b in enriched_positioning_beacons],
                y=[b["y"] for b in enriched_positioning_beacons],
                mode='markers+text',
                name='Positioning Beacons',
                marker=dict(
                    size=20, 
                    color='rgba(255, 0, 0, 0.3)',
                    symbol='square',
                    line=dict(width=3, color='red')
                ),
                text=[f"{b['name']}<br>Dist: {b['distance']:.1f}m" for b in enriched_positioning_beacons],
                textposition="top center",
                hovertemplate="<b>%{text}</b><br>Position: (%{x}, %{y})<br>RSSI: %{customdata}<extra></extra>",
                customdata=[b['rssi'] for b in enriched_positioning_beacons]
            ))
    
    # 3. История перемещений
    if history:
        history_df = pd.DataFrame(history)
        fig.add_trace(go.Scatter(
            x=history_df['x'],
            y=history_df['y'],
            mode='lines+markers',
            name='Movement Path',
            line=dict(color='blue', width=3),
            marker=dict(size=6, color='blue'),
            hoverinfo='skip'
        ))
    
    # 4. Текущая позиция
    fig.add_trace(go.Scatter(
        x=[current_pos['x']],
        y=[current_pos['y']],
        mode='markers+text',
        name='Current Position',
        marker=dict(
            size=20, 
            color='green', 
            symbol='circle',
            line=dict(width=3, color='darkgreen')
        ),
        text=['YOU ARE HERE'],
        textposition="bottom center",
        hovertemplate="<b>Current Position</b><br>(%{x:.2f}, %{y:.2f})<extra></extra>"
    ))
    
    # Настройки карты
    fig.update_layout(
        xaxis_title="X Position (meters)",
        yaxis_title="Y Position (meters)",
        showlegend=True,
        height=700,
        xaxis=dict(
            range=[x_min, x_max], 
            gridcolor='lightgray', 
            dtick=1,
            scaleanchor="y",
            scaleratio=1
        ),
        yaxis=dict(
            range=[y_min, y_max], 
            gridcolor='lightgray', 
            dtick=1
        ),
        plot_bgcolor='white'
    )
    
    return fig

def main():
    # Инициализация клиента MQTT
    if 'mqtt_client' not in st.session_state:
        st.session_state.mqtt_client = MQTTWebSocketClient()
        st.session_state.mqtt_client.start()
    
    client = st.session_state.mqtt_client

    if 'route_started' not in st.session_state:
        st.session_state.route_started = False

    # st_autorefresh(interval=500, key="data_refresh")
    
    with st.sidebar:
        refresh_rate = st.sidebar.slider(
            "Частота обновления (Гц)",
            min_value=0.1,
            max_value=10.0,
            value=2.0,
            step=0.1,
            help="Установите частоту обновления данных"
        )
        
        # Ползунок для выбора частоты
        refresh_interval = int(1000 / refresh_rate) 
        
        st_autorefresh(interval=refresh_interval, key="data_refresh")
        
        st.sidebar.write(f"**Текущая частота:** {refresh_rate} Гц")
        st.sidebar.write(f"**Интервал:** {refresh_interval} мс")
        st.header("Beacon Configuration")
        # Загрузка файла конфигурации
        uploaded_file = st.file_uploader(
            "Загрузите standart.beacons",
            type=['beacons'],
            key="beacon_uploader",
            help="Файл в формате: Name;X;Y"
        )
        
        if uploaded_file is not None:
            try:
                lines = uploaded_file.getvalue().decode('utf-8').splitlines()
                beacons_dict = {}
                
                for line in lines[1:]:
                    if line.strip():
                        name, x, y = line.strip().split(';')
                        beacons_dict[name] = {
                            'x': float(x),
                            'y': float(y),
                            'name': name
                        }
                
                if beacons_dict:
                    if st.button("Добавить маяки", use_container_width=True):
                        if client.publish_beacon_config(beacons_dict):
                            st.success("Маяки добавлены в систему")
                            # Обновляем локальную конфигурацию
                            client.beacon_config.update(beacons_dict)
                        else:
                            st.error("Ошибка при добавлении маяков")
                    
                    # Показываем предпросмотр загруженных данных
                    with st.expander("Предпросмотр загруженных маяков"):
                        preview_data = []
                        for name, beacon in list(beacons_dict.items())[:10]:
                            preview_data.append({"Name": name, "X": beacon['x'], "Y": beacon['y']})
                        if preview_data:
                            st.dataframe(preview_data)
                        if len(beacons_dict) > 10:
                            st.write(f"... и еще {len(beacons_dict) - 10} маяков")
                                    
            except Exception as e:
                st.error(f"Ошибка при обработке файла: {e}")
                st.info("Убедитесь, что файл соответствует формату:\nName;X;Y\nbeacon_1;3.0;-2.4")

        if client.beacon_config:
            if st.button("Очистить конфигурацию", type="secondary"):
                client.beacon_config = {}
                st.success("Конфигурация очищена")

        # Кнопка "Начать маршрут"
        st.subheader("Управление маршрутом")
        
        beacons_loaded = len(client.beacon_config) > 0
        if beacons_loaded:
            st.success(f"Готово! Загружено маяков: {len(client.beacon_config)}")
        
        if st.button(
            "Начать маршрут",
            type="primary",
            disabled=not beacons_loaded,
            help="Загрузите конфигурацию маяков для активации" if not beacons_loaded else "Начать построение маршрута"
        ):
            start_command = {"command": "start_routing", "ms": refresh_interval}
            client.client.publish("navigation/route/control", json.dumps(start_command))
            st.session_state.route_started = True
            st.success("Успешно!")
            
    # Основной интерфейс
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig = create_navigation_map(
            client.current_position, 
            client.beacon_config,
            client.positioning_beacons,
            client.positions_history
        )
        st.plotly_chart(fig, use_container_width=True)
        if st.session_state.route_started:
            st.markdown("---")
            col_end1, col_end2, col_end3 = st.columns([1, 2, 1])
            with col_end2:
                if st.button(
                    "🛑 Завершить маршрут",
                    type="secondary",
                    use_container_width=True,
                    help="Завершить текущий маршрут и сбросить навигацию"
                ):
                    end_command = {"command": "end_routing"}
                    client.client.publish("navigation/route/control", json.dumps(end_command))
                    st.session_state.route_started = False
                    st.success("Маршрут завершен!")
                    st.rerun()
            st.info("Маршрут активен")
        else:
            st.info("Маршрут не активен")
    
    
    with col2:
        st.metric(
            label="Current Position", 
            value=f"({client.current_position['x']:.2f}, {client.current_position['y']:.2f})"
        )

        status_color = "🟢" if client.connected else "🔴"
        st.write(f"{status_color} MQTT WebSocket: {'Подключен' if client.connected else 'Что-то не так'}")

        st.subheader("Мояки для позиции")
        if client.positioning_beacons:
            for beacon in client.positioning_beacons:
                beacon_name = beacon.get('name', 'Unknown')
                with st.expander(f"Опа {beacon_name}"):
                    st.write(f"**RSSI:** {beacon.get('rssi', 'N/A')} dBm")
                    st.write(f"**Distance:** {beacon.get('distance', 'N/A'):.2f}m")
                    if beacon_name in client.beacon_config:
                        pos = client.beacon_config[beacon_name]
                        st.write(f"**Position:** ({pos['x']}, {pos['y']})")
        else:
            st.info("Надо запустить скорее всего")
        
        st.subheader("Все маяки")
        if client.beacon_config:
            for name, beacon in list(client.beacon_config.items())[:8]:
                st.write(f"{name} - ({beacon['x']}, {beacon['y']})")
            if len(client.beacon_config) > 8:
                st.write(f"... и еще {len(client.beacon_config) - 8}")
        else:
            st.warning("Не загрузили маяки")
        
        st.subheader("История позиций")
        if client.positions_history:
            history_df = pd.DataFrame(client.positions_history[-8:])
            st.dataframe(
                history_df[['x', 'y', 'timestamp']].tail(5), 
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Нету пока, запусти")
            

if __name__ == "__main__":
    main()