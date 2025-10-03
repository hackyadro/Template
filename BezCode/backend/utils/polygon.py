import math

def cross(o, a, b):
        return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])

def simple_convex_hull(points):
    """Простая реализация выпуклой оболочки"""
    if len(points) <= 2:
        return points
    
    points = sorted(points)
    
    lower = []
    for p in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
        
    upper = []
    for p in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
        
    return lower[:-1] + upper[:-1]

def is_point_inside_polygon(point, polygon):
    """Проверяет, находится ли точка внутри многоугольника"""
    x, y = point
    n = len(polygon)
    inside = False
    
    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    
    return inside

def distance_point_to_segment(point, seg_start, seg_end):
    """Возвращает расстояние от точки до отрезка и ближайшую точку на отрезке"""
    x, y = point
    x1, y1 = seg_start
    x2, y2 = seg_end
    
    dx, dy = x2 - x1, y2 - y1
    
    if dx == 0 and dy == 0:
        return math.sqrt((x - x1)**2 + (y - y1)**2), (x1, y1)
    
    t = ((x - x1) * dx + (y - y1) * dy) / (dx**2 + dy**2)
    t = max(0, min(1, t))
    
    closest_x = x1 + t * dx
    closest_y = y1 + t * dy
    
    return math.sqrt((x - closest_x)**2 + (y - closest_y)**2), (closest_x, closest_y)

def move_point_inside(point, polygon, margin = 0.1):
    """
    Если точка снаружи многоугольника, сдвигает её внутрь.
    margin - отступ от границы (по умолчанию 0.1)
    """
    if is_point_inside_polygon(point, polygon):
        return point
    
    min_distance = float('inf')
    closest_point = None
    
    n = len(polygon)
    for i in range(n):
        seg_start = polygon[i]
        seg_end = polygon[(i + 1) % n]
        
        distance, closest = distance_point_to_segment(point, seg_start, seg_end)
        
        if distance < min_distance:
            min_distance = distance
            closest_point = closest
    
    if closest_point is None:
        return point
    
    center_x = sum(p[0] for p in polygon) / len(polygon)
    center_y = sum(p[1] for p in polygon) / len(polygon)
    
    dx = center_x - closest_point[0]
    dy = center_y - closest_point[1]
    
    length = math.sqrt(dx**2 + dy**2)
    if length > 0:
        dx, dy = dx/length, dy/length
    
    new_x = closest_point[0] + dx * margin
    new_y = closest_point[1] + dy * margin
    
    return (new_x, new_y)