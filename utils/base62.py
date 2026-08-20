BASE62="0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

def encode(num:int) -> str:
    if num==0:
        return BASE62[0]
    result=""
    while num>0:
        remainder=num%62
        result=BASE62[remainder]+result
        num//=62

    return result

def decode(code:str) -> int:
    num=0
    for char in code:
        num=num*62+BASE62.index(char)

    return num