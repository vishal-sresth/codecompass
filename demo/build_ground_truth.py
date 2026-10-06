"""Builds ground_truth.json: 12 hand-picked rules; expected values read from config/development.toml."""
import re, json, os
REPO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hyperswitch")
F = "config/development.toml"
PICK = [  # (connector section, payment method, PM question)
 ("stripe","affirm","Where can we offer Affirm through Stripe, and in which currency?"),
 ("stripe","cashapp","Which countries and currencies is Cash App Pay available in on Stripe?"),
 ("stripe","eps","Where is EPS available on Stripe?"),
 ("stripe","giropay","Why can't we use Giropay on Stripe outside Germany?"),
 ("stripe","ideal","Which countries can use iDEAL on Stripe?"),
 ("stripe","klarna","Why is Klarna on Stripe available in Germany but not in India?"),
 ("adyen","mb_way","Where is MB Way available on Adyen?"),
 ("adyen","pay_bright","Which countries and currencies does PayBright on Adyen support?"),
 ("adyen","walley","In which markets can customers pay with Walley on Adyen?"),
 ("adyen","mobile_pay","Where is MobilePay available on Adyen?"),
 ("adyen","affirm","Is Affirm available on Adyen, and where?"),
 ("flexiti","flexiti","Which countries support Flexiti?"),
]
TRICKS = [
 "What minimum customer age is required to use Klarna on Stripe?",
 "What is the refund window in days for Giropay payments on Stripe?",
 "What cooling-off period applies to Afterpay payments in the UK?",
]
lines = open(os.path.join(REPO, F)).read().splitlines()
sec = None; found = {}
for i, l in enumerate(lines, 1):
    m = re.match(r"^\[pm_filters\.(\w+)\]", l)
    if m: sec = m.group(1); continue
    if l.startswith("["): sec = None; continue
    m = re.match(r"^(\w+) = \{(.*)\}", l)
    if sec and m:
        c = re.search(r'country = "([^"]*)"', m.group(2)); u = re.search(r'currency = "([^"]*)"', m.group(2))
        found[(sec, m.group(1))] = (i, [x.strip() for x in c.group(1).split(",")] if c else [], [x.strip() for x in u.group(1).split(",")] if u else [])
rules = []
for n, (con, pm, q) in enumerate(PICK, 1):
    i, co, cu = found[(con, pm)]
    rules.append({"id": f"R{n}", "question": q, "connector": con, "payment_method": pm, "countries": co, "currencies": cu, "file": F, "line": i})
gt = {"repo": "juspay/hyperswitch", "rules": rules, "tricks": [{"id": f"T{n}", "question": q} for n, q in enumerate(TRICKS, 1)]}
json.dump(gt, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ground_truth.json"), "w"), indent=2)
for r in rules: print(r["id"], r["connector"], r["payment_method"], f'{F}:{r["line"]}', len(r["countries"]), "countries", r["currencies"][:3])
