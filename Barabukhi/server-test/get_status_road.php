<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST');
header('Access-Control-Allow-Headers: Content-Type');

// Константа со статусом записи маршрута (потом будем подтягивать из БД)
const WRITE_ROAD_STATUS = true;

// Проверяем, что это POST запрос
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method not allowed. Use POST']);
    exit;
}

// Получаем данные из POST запроса
$input = file_get_contents('php://input');
$data = json_decode($input, true);

// Проверяем наличие параметра mac
$mac = null;
if (isset($data['mac'])) {
    $mac = $data['mac'];
} elseif (isset($_POST['mac'])) {
    $mac = $_POST['mac'];
}

if (empty($mac)) {
    http_response_code(400);
    echo json_encode(['error' => 'Parameter mac is required']);
    exit;
}

// Валидация MAC адреса (опционально)
if (!preg_match('/^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/', $mac)) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid MAC address format']);
    exit;
}

// Здесь потом будет логика получения данных из БД по MAC адресу
// Пока возвращаем константу
$response = [
    'write_road' => WRITE_ROAD_STATUS
];

// Отправляем JSON ответ
echo json_encode($response);
