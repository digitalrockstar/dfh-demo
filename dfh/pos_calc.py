"""Bill arithmetic shared by the API and mirrored in frontend/src/pos_store.js. Integer paise, half up, tax inside the price."""

def half_up_div(a, b):
    return (2 * a + b) // (2 * b)


def line_calc(uom, unit_price, qty, discount, rate_pct):
    """uom 'g': unit_price is per kg and qty is grams. uom 'ea': unit_price per piece."""
    gross = half_up_div(unit_price * qty, 1000) if uom == "g" else unit_price * qty
    net = gross - discount
    bp = int(round(rate_pct * 100))
    tax = half_up_div(net * bp, 10000 + bp) if net > 0 else 0
    return gross, net, tax


def bill_calc(lines):
    """lines: list of dict(gross, discount, net, tax). Returns totals with round off to the rupee."""
    gross = sum(l["gross"] for l in lines); disc = sum(l["discount"] for l in lines)
    net = sum(l["net"] for l in lines); tax = sum(l["tax"] for l in lines)
    total = ((net + 50) // 100) * 100
    return dict(gross=gross, discount=disc, tax=tax, round_off=total - net, total=total)
