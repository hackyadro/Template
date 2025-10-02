<?php

// echo json_encode($_POST);

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

// Логика определения изменений (здесь можно добавить свою логику)
// Для примера, генерируем случайные данные
$change = (bool)rand(0, 1);
$change_list = [];

if ($change) {
    // Возможные типы изменений
    $possible_changes = ["map", "freq", "status"];
    
    // Выбираем случайное количество изменений (1-3)
    $num_changes = rand(1, 3);
    $change_list = array_rand(array_flip($possible_changes), $num_changes);
    
    // Если выбрано только одно изменение, array_rand возвращает строку, а не массив
    if (!is_array($change_list)) {
        $change_list = [$change_list];
    }
}

// Формируем ответ
$response = [
    'change' => $change,
    'change_list' => $change_list
];

// Отправляем JSON ответ
echo json_encode($response);