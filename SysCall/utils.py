

import streamlit as st
# загрузка позиций маячков
def load_beacon_positions(filename):
    positions = {}
    try:
        with open(filename, 'r') as f:
            next(f)
            for line in f:
                parts = line.strip().split(';')
                if len(parts) == 3:
                    name, x, y = parts
                    positions[name] = (float(x), float(y))
        print(f"Загружены маячки из '{filename}': {positions}")
        return positions
    except Exception as e:
        st.error(f"Ошибка загрузки файла '{filename}': {e}")
        return None

# скачивание пути
def format_path_data_for_download(path_data):
    header = "X;Y\n"
    lines = [f"{point['x']};{point['y']}" for point in path_data]
    return header + "\n".join(lines)