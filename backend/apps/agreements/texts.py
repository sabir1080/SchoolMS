"""The agreement texts. Changing the wording means a new VERSION; agreements already signed keep their own copy."""

from decimal import Decimal

TRIAL_VERSION = "2026.1"
SUBSCRIPTION_VERSION = "2026.1"


def _money(amount, currency):
    return f"{currency} {Decimal(amount):,.0f}" if amount is not None else "—"


def trial_sections(provider, trial_days):
    p = provider["business_name"]
    return [
        {"heading": "1. The free trial", "body": (
            f"{p} gives the Institute the use of SchoolMS free of charge for {trial_days} days from registration, "
            "with the features of the plan shown in the app. No payment is due for the trial."
        )},
        {"heading": "2. After the trial", "body": (
            "When the trial ends, the Institute's users can only see the Plan & Billing page until the Institute signs a "
            "subscription agreement and pays. Nothing is charged automatically."
        )},
        {"heading": "3. The Institute's data", "body": (
            "All data the Institute enters (students, parents, staff, fees, results and other records) belongs to the "
            f"Institute. {p} uses it only to provide the service, keeps it private from other institutes and does not sell it. "
            f"If the Institute does not subscribe, its data is kept for {provider['data_retention_days']} days after the trial "
            "ends and may then be deleted. The Institute may ask for a copy before that."
        )},
        {"heading": "4. The Institute's responsibilities", "body": (
            "The Institute keeps its passwords safe, enters correct information, and has the consent needed to store "
            "the details of its students, parents and staff and to send them messages."
        )},
        {"heading": "5. The service", "body": (
            f"{p} provides the service as it is during the trial and works to keep it available and secure, but does not "
            "guarantee it will never be interrupted. Either party may end the trial at any time."
        )},
        {"heading": "6. Law", "body": "This agreement is governed by the laws of Pakistan."},
    ]


def subscription_sections(provider, schedule):
    p = provider["business_name"]
    grace = provider["grace_days"]
    keep = provider["data_retention_days"]
    return [
        {"heading": "1. The service", "body": (
            f"{p} provides the Institute with SchoolMS, an online school management system, under the plan, period and "
            "fees in the Schedule above, for the Institute's own use."
        )},
        {"heading": "2. Fees and payment", "body": (
            f"The fee for each {schedule['cycle']} period is {schedule['price']}, payable in advance. "
            f"The subscription starts when {p} receives the payment and records it in SchoolMS. "
            f"{provider['refund_policy']}"
        )},
        {"heading": "3. Renewal and late payment", "body": (
            "The subscription does not renew or charge automatically; the Institute renews by signing and paying again. "
            f"If a renewal payment is late, {p} may give a grace period of up to {grace} days, after which the Institute's "
            "users can only see the Plan & Billing page until payment is made. No data is deleted because of late payment "
            "within the retention period below."
        )},
        {"heading": "4. Plan limits and changes", "body": (
            f"The plan allows up to {schedule['students_limit']} active students and {schedule['staff_limit']} staff "
            "logins. The Institute may move to another plan by signing a new agreement. "
            f"{p} may change its prices for future periods with at least 30 days' notice; the current period is not affected."
        )},
        {"heading": "5. The Institute's data", "body": (
            "All data the Institute enters belongs to the Institute. "
            f"{p} uses it only to provide the service, keeps it separate from other institutes, protects it with reasonable "
            "security and backups, and does not sell or share it except where the law requires. "
            f"After the subscription ends the data is kept for {keep} days, during which the Institute may renew or ask for a copy; "
            "after that it may be deleted."
        )},
        {"heading": "6. The Institute's responsibilities", "body": (
            "The Institute keeps its passwords safe and controls who has a login, enters correct information, and has the "
            "consent needed to store the details of its students, parents and staff and to send them messages. "
            "Online fee payments go to the Institute's own merchant accounts (JazzCash, Easypaisa, Safepay, Stripe or others); "
            "the Institute is responsible for those accounts and their charges."
        )},
        {"heading": "7. Availability and support", "body": (
            f"{p} works to keep the service available, secure and backed up, and to fix problems quickly, but does not "
            "guarantee uninterrupted service. Planned maintenance is kept short and, where possible, announced in advance. "
            f"Support is given through the contact details of {p} above."
        )},
        {"heading": "8. Limit of liability", "body": (
            f"{p} is not liable for indirect losses, or for losses caused by events outside its reasonable control. "
            f"Its total liability under this agreement is limited to the fees the Institute paid for the current period."
        )},
        {"heading": "9. Ending the agreement", "body": (
            "Either party may end this agreement at the end of a paid period. "
            f"{p} may suspend the service if the Institute misuses it or breaks the law, after notice where possible. "
            "Sections 5 and 8 continue after the agreement ends."
        )},
        {"heading": "10. Electronic signature and law", "body": (
            "The Institute's representative signs by typing their full name; this has the same effect as a handwritten signature. "
            "This agreement is governed by the laws of Pakistan, and both parties will first try to settle any dispute by discussion."
        )},
    ]


def schedule_for(plan, cycle, price, currency, labels):
    return {
        "plan": plan.name,
        "plan_code": plan.code,
        "cycle": cycle,
        "cycle_label": "Yearly (365 days)" if cycle == "yearly" else "Monthly (30 days)",
        "price": _money(price, currency),
        "students_limit": plan.max_students if plan.max_students else "unlimited",
        "staff_limit": plan.max_staff if plan.max_staff else "unlimited",
        "features": labels,
    }
