"""A small, fixed corpus for evaluating retrieval quality without needing Postgres.

Each document is a distinct policy topic; each eval case is a natural-language query
paired with the id of the document that should be retrieved to answer it.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class EvalDocument:
    id: str
    text: str


@dataclass(frozen=True)
class EvalCase:
    query: str
    expected_document_id: str


DOCUMENTS = [
    EvalDocument(
        id="refunds",
        text=(
            "Refund Policy. If you are not satisfied with your purchase, you may request a "
            "refund within 30 days of the delivery date. Refunds are issued to the original "
            "payment method and typically appear within 5 to 7 business days. Items must be "
            "returned in their original condition. Digital products and gift cards are not "
            "eligible for refunds."
        ),
    ),
    EvalDocument(
        id="shipping",
        text=(
            "Shipping Information. Standard shipping takes 3 to 5 business days within the "
            "continental US and 7 to 14 business days internationally. Express shipping is "
            "available at checkout for an additional fee and delivers within 1 to 2 business "
            "days. Orders placed after 2pm local time ship the following business day."
        ),
    ),
    EvalDocument(
        id="warranty",
        text=(
            "Warranty Coverage. All hardware products include a 1 year limited warranty "
            "covering manufacturing defects. The warranty does not cover accidental damage, "
            "water damage, or unauthorized repairs. To make a warranty claim, contact support "
            "with your order number and a description of the issue."
        ),
    ),
    EvalDocument(
        id="privacy",
        text=(
            "Privacy Policy. We collect your email address and shipping details solely to "
            "process orders and provide customer support. We do not sell personal information "
            "to third parties. You may request a copy of your data or ask us to delete your "
            "account at any time by emailing privacy@example.com."
        ),
    ),
    EvalDocument(
        id="account_deletion",
        text=(
            "Closing Your Account. You can permanently delete your account from the Settings "
            "page under 'Danger Zone'. This removes your order history, saved addresses, and "
            "payment methods. Account deletion cannot be undone, so consider deactivating "
            "instead if you might come back later."
        ),
    ),
]

EVAL_CASES = [
    EvalCase("How long do I have to return something?", "refunds"),
    EvalCase("When will I get my money back after a return?", "refunds"),
    EvalCase("How fast is delivery to another country?", "shipping"),
    EvalCase("Does the express option arrive next day?", "shipping"),
    EvalCase("Is water damage covered under warranty?", "warranty"),
    EvalCase("What do I need to file a warranty claim?", "warranty"),
    EvalCase("Do you sell my data to advertisers?", "privacy"),
    EvalCase("Can I get a copy of the personal data you hold on me?", "privacy"),
    EvalCase("How do I permanently remove my account?", "account_deletion"),
    EvalCase("Can I undo deleting my account?", "account_deletion"),
]
