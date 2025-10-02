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

# Настройка страницы
st.set_page_config(
    page_title="Indoor Navigation",
    page_icon="📍",
    layout="wide"
)

class MQTTWebSocketClient:
    def __init__(self):
        self.client = mqtt.Client(client_id="FrontendWS", transport="websockets")
        self.current_position = {"x": 2.5, "y": 2.5}
        self.beacons_data = []  # Все обнаруженные маяки
        self.used_beacons = []
        self.positions_history = []
        self.connected = False
        self.all_beacons = self.load_all_beacons()  # Загружаем ВСЕ маяки из файла
        
    def load_all_beacons(self):
        beacons = {}
        try:
            beacons_file = "/app/data/standart.beacons"
            if os.path.exists(beacons_file):
                with open(beacons_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines[1:]:  # Пропускаем заголовок
                        if line.strip():
                            name, x, y = line.strip().split(';')
                            beacons[name] = {
                                'x': float(x),
                                'y': float(y),
                                'name': name
                            }
                print(f"✅ Loaded {len(beacons)} beacons from file")
        except Exception as e:
            print(f"❌ Error loading beacons: {e}")
        return beacons
        
    def on_connect(self, client, userdata, flags, rc):
        self.connected = True
        st.success("✅ Connected to MQTT via WebSocket")
        client.subscribe("navigation/position/current")
        client.subscribe("ble/beacons/raw")
        client.subscribe("system/status")
        
    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            
            if msg.topic == "navigation/position/current":
                self.current_position = {
                    "x": payload['x'],
                    "y": payload['y'],
                    "timestamp": payload.get('timestamp', time.time())
                }
                self.used_beacons = payload.get('used_beacons', [])
                
                self.positions_history.append({
                    'x': self.current_position['x'],
                    'y': self.current_position['y'],
                    'timestamp': self.current_position['timestamp']
                })
                # Сохраняем только последние 50 позиций
                if len(self.positions_history) > 50:
                    self.positions_history.pop(0)
                    
            elif msg.topic == "ble/beacons/raw":
                self.beacons_data = payload.get('beacons', [])
                
        except json.JSONDecodeError as e:
            st.error(f"JSON decode error: {e}")
            
    def start(self):
        try:
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            # Подключаемся к WebSocket порту
            self.client.connect("mqtt-broker", 9001, 60)
            threading.Thread(target=self.client.loop_forever, daemon=True).start()
        except Exception as e:
            st.error(f"WebSocket connection error: {e}")

def create_navigation_map(current_pos, all_beacons, used_beacons, history):
    fig = go.Figure()
    
    # Определяем границы карты на основе позиций маяков
    if all_beacons:
        x_coords = [beacon['x'] for beacon in all_beacons.values()]
        y_coords = [beacon['y'] for beacon in all_beacons.values()]
        x_min, x_max = min(x_coords) - 1, max(x_coords) + 1
        y_min, y_max = min(y_coords) - 1, max(y_coords) + 1
    else:
        x_min, x_max, y_min, y_max = -1, 6, -1, 6
    
    # Добавляем сетку помещения
    fig.add_shape(type="rect", x0=x_min, y0=y_min, x1=x_max, y1=y_max, 
                  line=dict(color="black", width=2), fillcolor="lightgray", opacity=0.1)
    
    # Добавляем историю перемещений (линия)
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
    
    # ВСЕ маяки из файла (серым)
    if all_beacons:
        all_beacon_list = list(all_beacons.values())
        fig.add_trace(go.Scatter(
            x=[b["x"] for b in all_beacon_list],
            y=[b["y"] for b in all_beacon_list],
            mode='markers+text',
            name='All Beacons',
            marker=dict(size=15, color='lightgray', symbol='square', 
                       line=dict(width=1, color='darkgray')),
            text=[b["name"] for b in all_beacon_list],
            textposition="top center",
            hovertemplate="<b>%{text}</b><br>Position: (%{x}, %{y})<extra></extra>"
        ))
    
    # Использованные для позиционирования маяки (красным с обводкой)
    used_beacon_positions = []
    for b in used_beacons:
        pos = b.get("position") or {}
        name = b.get("name") or "Beacon"
        if pos and "x" in pos and "y" in pos:
            used_beacon_positions.append({
                "x": pos["x"],
                "y": pos["y"],
                "name": name,
                "distance": b.get("distance", 0)
            })
    
    if used_beacon_positions:
        # Большие маркеры с толстой обводкой для использованных маяков
        fig.add_trace(go.Scatter(
            x=[b["x"] for b in used_beacon_positions],
            y=[b["y"] for b in used_beacon_positions],
            mode='markers+text',
            name='Positioning Beacons',
            marker=dict(
                size=25, 
                color='rgba(255, 0, 0, 0.3)',  # Полупрозрачная заливка
                symbol='square',
                line=dict(width=3, color='red')  # Толстая красная обводка
            ),
            text=[f"{b['name']}<br>Dist: {b['distance']}m" for b in used_beacon_positions],
            textposition="top center",
            hovertemplate="<b>%{text}</b><br>Position: (%{x}, %{y})<extra></extra>"
        ))
    
    # Добавляем текущую позицию
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
        title="🏠 Real-Time Indoor Navigation - LIVE",
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
    st.title("📍 Real-Time Indoor Navigation")
    
    if 'mqtt_client' not in st.session_state:
        st.session_state.mqtt_client = MQTTWebSocketClient()
        st.session_state.mqtt_client.start()
    
    client = st.session_state.mqtt_client
    
    st_autorefresh(interval=500, key="data_refresh")
    
    # Основной интерфейс
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Live Position Map")
        
        # Карта навигации
        fig = create_navigation_map(
            client.current_position, 
            client.all_beacons,  # Используем ВСЕ маяки из файла
            client.used_beacons,
            client.positions_history
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Real-time Data")
        
        # Текущая позиция
        st.metric(
            label="Current Position", 
            value=f"({client.current_position['x']:.2f}, {client.current_position['y']:.2f})"
        )
        
        # Статус подключения
        status_color = "🟢" if client.connected else "🔴"
        st.write(f"{status_color} MQTT WebSocket: {'Connected' if client.connected else 'Disconnected'}")
        
        # Использованные маяки для позиционирования
        st.subheader("Positioning Beacons")
        if client.used_beacons:
            for beacon in client.used_beacons:
                with st.expander(f"🎯 {beacon.get('name', 'Unknown')}"):
                    st.write(f"**RSSI:** {beacon.get('rssi', 'N/A')} dBm")
                    pos = beacon.get('position', {})
                    st.write(f"**Position:** ({pos.get('x', 'N/A')}, {pos.get('y', 'N/A')})")
                    st.write(f"**Distance:** {beacon.get('distance', 'N/A'):.2f}m")
        else:
            st.info("No positioning beacons available")
        
        # Все обнаруженные маяки (из последнего MQTT сообщения)
        st.subheader("Currently Detected Beacons")
        if client.beacons_data:
            for beacon in client.beacons_data:
                st.write(f"📶 {beacon.get('name', 'Unknown')} - RSSI: {beacon.get('rssi', 'N/A')} dBm")
        else:
            st.info("No beacons detected in last message")
        
        # Все маяки из файла
        st.subheader("All Available Beacons")
        if client.all_beacons:
            for name, beacon in list(client.all_beacons.items())[:10]:  # Показываем первые 10
                st.write(f"📍 {name} - Position: ({beacon['x']}, {beacon['y']})")
            if len(client.all_beacons) > 10:
                st.write(f"... and {len(client.all_beacons) - 10} more")
        else:
            st.info("No beacon configuration loaded")
        
        # История позиций
        st.subheader("Position History")
        if client.positions_history:
            history_df = pd.DataFrame(client.positions_history[-10:])  # Последние 10
            st.dataframe(history_df.tail(5), use_container_width=True)
        else:
            st.info("No position history yet")
    
    # Системная информация
    with st.expander("System Information"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write("**MQTT Topics:**")
            st.code("""
navigation/position/current
ble/beacons/raw  
system/status
            """)
        
        with col2:
            st.write("**WebSocket:**")
            st.write("Port: 9001")
            st.write(f"Status: {'Connected' if client.connected else 'Disconnected'}")
            
        with col3:
            st.write("**Last Update:**")
            st.write(time.strftime("%H:%M:%S"))

if __name__ == "__main__":
    main()