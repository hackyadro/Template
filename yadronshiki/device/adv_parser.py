import ubinascii

class BeaconParser:
    @staticmethod
    def adv_parse(advertising_bytes):
        result = {"local_name": None, "manuf_data": None, "service_data": []}
        i, b = 0, advertising_bytes
        while i < len(b) - 1:
            length = b[i]
            if length == 0 or i + length >= len(b):
                break
            ad_type = b[i + 1]
            data = b[i + 2 : i + 1 + length]

            if ad_type in (0x08, 0x09):  
                try:
                    result["local_name"] = data.decode('utf-8', 'ignore')
                except:
                    pass
            elif ad_type == 0xFF:  
                result["manuf_data"] = data
            elif ad_type == 0x16:  
                if len(data) >= 2:
                    uuid16, svc = data[0:2], data[2:]
                    result["service_data"].append((uuid16, svc))
            i += 1 + length
        return result

    @staticmethod
    def parse_ibeacon(manuf):
        if manuf and len(manuf) >= 23 and manuf[0:2] == b'\x4c\x00' and manuf[2:4] == b'\x02\x15':
            uuid = ubinascii.hexlify(manuf[4:20]).decode().upper()
            uuid = f"{uuid[0:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:32]}"
            return {
                "type": "iBeacon",
                "uuid": uuid,
                "major": int.from_bytes(manuf[20:22], 'big'),
                "minor": int.from_bytes(manuf[22:24], 'big'),
                "tx": int.from_bytes(manuf[24:25], 'big', signed=True) if len(manuf) > 24 else None,
            }
        return None
