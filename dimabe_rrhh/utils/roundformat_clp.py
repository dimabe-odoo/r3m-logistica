from math import floor, ceil


def round_clp(value):
    value_str = str(value)
    list_value = value_str.split('.')
    if len(list_value) > 1:
        decimal = int(list_value[1][0])
        if decimal == 0:
            return format_clp(int(value))
        elif decimal < 5:
            return format_clp(floor(value))
        else:
            return format_clp(ceil(value))

    else:
        return format_clp(value)

def format_clp(value):
    return '{:,}'.format(value).replace(',', '.')
