<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST');
header('Access-Control-Allow-Headers: Content-Type');

// Проверяем, что это POST запрос
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method not allowed. Use POST']);
    exit;
}

// Получаем данные из POST запроса
$input = file_get_contents('php://input');
$data = json_decode($input, true);

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

$map_name = null;
if (isset($data['map_name'])) {
    $map_name = $data['map_name'];
} elseif (isset($_POST['map_name'])) {
    $map_name = $_POST['map_name'];
}

if (empty($map_name)) {
    http_response_code(400);
    echo json_encode(['error' => 'Parameter map_name is required']);
    exit;
}

$list = null;
if (isset($data['list'])) {
    $list = $data['list'];
} elseif (isset($_POST['list'])) {
    $list = $_POST['list'];
}

if (empty($list)) {
    http_response_code(400);
    echo json_encode(['error' => 'Parameter list is required and must be an array']);
    exit;
}

$response = [
    'accept' => true
];

// Отправляем JSON ответ
echo json_encode($response);

// $list = json_decode(json_encode($list), true);

// // Валидация MAC адреса
// if (!preg_match('/^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/', $mac)) {
//     http_response_code(400);
//     echo json_encode(['error' => 'Invalid MAC address format']);
//     exit;
// }

// Валидация структуры списка сигналов
// foreach ($list as $index => $signal_data) {
//     if (!is_array($signal_data)) {
//         http_response_code(400);
//         echo json_encode(['error' => "List item at index $index must be an object"]);
//         exit;
//     }
    
//     if (!isset($signal_data['name']) || !isset($signal_data['signal'])) {
//         http_response_code(400);
//         echo json_encode(['error' => "List item at index $index must contain 'name' and 'signal' fields"]);
//         exit;
//     }
// }

// Здесь потом будет логика сохранения данных в БД
// Пока что просто логируем полученные данные (можно убрать в продакшене)
// error_log("Received signal data - MAC: $mac, Map: $map_name, Signals count: " . count($list));

// Возвращаем подтверждение

