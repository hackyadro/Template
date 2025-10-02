def decode_fields(payload):
    """
    Разбирает рекламные данные и находит поле по заданному типу.
    Возвращает список найденных полей.
    """
    idx = 0
    results = dict()
    while idx < len(payload):
        length = payload[idx]
        if length == 0:
            break
        if idx + length >= len(payload):
            break
            
        type_field = payload[idx + 1]
        data_start = idx + 2
        data_end = idx + length + 1
        
        results[type_field] = bytes(payload[data_start:data_end])
        
        idx += length + 1
    return results