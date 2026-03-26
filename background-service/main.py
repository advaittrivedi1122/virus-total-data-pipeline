import time
import json
import asyncio
from service import BackgroundService, Identifiers


class _MyBreak(Exception):
    pass


_data = None
with open("background-service/data.json", "r") as json_data:
    _data = json.load(json_data)
    json_data.close()


len_ip = len(_data["ip"])
len_domain = len(_data["domain"])
len_filehash = len(_data["filehash"])

index = {
    "ip": 0,
    "domain": 0,
    "filehash": 0
}

_counter = 1

async def infinite_loop(fn, *args, **kwargs):
    global _counter
    while True:
        print("-------------- Processing -----------------")
        await fn(*args, **kwargs)


async def background(_service: BackgroundService):
    global _counter
    counter = _counter
    updated = False
    try:
        match counter:
            case Identifiers.IP.value:
                if index["ip"] < len_ip:
                    identifier = _data["ip"][index["ip"]]
                    res = _service.check_in_db(identifier, Identifiers.IP.value)
                    if not res.get("error"):
                        updated = True
                        index["ip"] += 1
                        raise _MyBreak() # found in db, return
                    print(f"Processing IP Address : {identifier}")
                    res = await _service.get_ip_address_data(_data["ip"][index["ip"]])
                    if not res.get("error"):
                        updated = True
                        index["ip"] += 1
            case Identifiers.DOMAIN.value:
                if index["domain"] < len_domain:
                    identifier = _data["domain"][index["domain"]]
                    res = _service.check_in_db(identifier, Identifiers.DOMAIN.value)
                    if not res.get("error"):
                        updated = True
                        index["domain"] += 1
                        raise _MyBreak() # found in db, return
                    print(f"Processing Domain : {_data["domain"][index["domain"]]}")
                    res = await _service.get_domain_data(_data["domain"][index["domain"]])
                    if not res.get("error"):
                        updated = True
                        index["domain"] += 1
            case Identifiers.FILEHASH.value:
                if index["filehash"] < len_filehash:
                    identifier = _data["filehash"][index["filehash"]]
                    res = _service.check_in_db(identifier, Identifiers.FILEHASH.value)
                    if not res.get("error"):
                        updated = True
                        index["filehash"] += 1
                        raise _MyBreak() # found in db, return
                    print(f"Processing File hash : {_data["filehash"][index["filehash"]]}")
                    res = await _service.get_filehash_data(_data["filehash"][index["filehash"]])
                    if not res.get("error"):
                        updated = True
                        index["filehash"] += 1
            case _:
                print("Default Case")
    except _MyBreak:
        pass

    if updated:
        print("Index :", index)
        _counter += 1
        if _counter > 3:
                _counter = 1
    print("----------------- Wait 15s ----------------")
    time.sleep(15)


def bye():
    print("\nBye!!")


async def main():
    _service: BackgroundService = BackgroundService()
    try:
        await infinite_loop(background, _service)
    except Exception as e:
        print("Error in infinite loop :", e)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        bye()
    except Exception as e:
        print("Error in Background Service :", e)