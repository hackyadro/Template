import streamlit as st
import json
import time
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
import paho.mqtt.client as mqtt
import threading

# Настройка страницы
st.set_page_config(
    page_title="Indoor Navigation",
    page_icon="📍",
    layout="wide"
)

class MQTTWebSocketClient:
    def __init__(self):
        # Для paho-mqtt 1.6.1 аргумент callback_api_version отсутствует
        self.client = mqtt.Client(client_id="FrontendWS", transport="websockets")
        self.current_position = {"x": 2.5, "y": 2.5}
        self.beacons_data = []
        self.positions_history = []
        self.connected = False
        
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
                self.current_position = payload
                self.positions_history.append({
                    'x': payload['x'],
                    'y': payload['y'],
                    'timestamp': payload.get('timestamp', time.time())
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

def create_navigation_map(current_pos, beacons_data, history):
    fig = go.Figure()
    
    # Добавляем сетку помещения
    fig.add_shape(type="rect", x0=0, y0=0, x1=5, y1=5, 
                  line=dict(color="black", width=2), fillcolor="lightgray", opacity=0.2)
    
    # Добавляем историю перемещений (линия)
    if history:
        history_df = pd.DataFrame(history)
        fig.add_trace(go.Scatter(
            x=history_df['x'],
            y=history_df['y'],
            mode='lines+markers',
            name='Movement Path',
            line=dict(color='blue', width=4),
            marker=dict(size=6, color='blue'),
            hoverinfo='skip'
        ))
    
    # Маячки: если пришли данные, рисуем их; иначе ничего не рисуем
    beacon_positions = []
    if beacons_data:
        for b in beacons_data:
            pos = b.get("position") or {}
            name = b.get("name") or b.get("mac") or "Beacon"
            if pos and "x" in pos and "y" in pos:
                beacon_positions.append({"x": pos["x"], "y": pos["y"], "name": name})
    
    beacon_x = [b["x"] for b in beacon_positions]
    beacon_y = [b["y"] for b in beacon_positions]
    beacon_names = [b["name"] for b in beacon_positions]
    
    if beacon_positions:
        fig.add_trace(go.Scatter(
            x=beacon_x,
            y=beacon_y,
            mode='markers+text',
            name='Beacons',
            marker=dict(size=25, color='red', symbol='square', line=dict(width=2, color='darkred')),
            text=beacon_names,
            textposition="top center",
            hovertemplate="<b>%{text}</b><br>Position: (%{x}, %{y})<extra></extra>"
        ))
    
    # Добавляем текущую позицию
    fig.add_trace(go.Scatter(
        x=[current_pos['x']],
        y=[current_pos['y']],
        mode='markers+text',
        name='Current Position',
        marker=dict(size=30, color='green', symbol='circle', line=dict(width=3, color='darkgreen')),
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
        width=800,
        xaxis=dict(range=[-1, 6], gridcolor='lightgray', dtick=1),
        yaxis=dict(range=[-1, 6], gridcolor='lightgray', dtick=1),
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
            client.beacons_data,
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
        
        # Данные маячков
        st.subheader("Detected Beacons")
        if client.beacons_data:
            for beacon in client.beacons_data:
                with st.expander(f"📶 {beacon.get('name', beacon.get('mac', 'Unknown'))}"):
                    st.write(f"**MAC:** {beacon.get('mac', 'N/A')}")
                    st.write(f"**RSSI:** {beacon.get('rssi', 'N/A')} dBm")
                    st.write(f"**Position:** ({beacon.get('position', {}).get('x', 'N/A')}, {beacon.get('position', {}).get('y', 'N/A')})")
        else:
            st.info("No beacons detected")
        
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