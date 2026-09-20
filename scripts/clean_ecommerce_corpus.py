"""Clean and structure crawled eBay policy documents for K4-L3B.

Cleans data/ecommerce-crawled-final/ documents:
1. Strips server logs (rlogid), search widgets, and 'On this page' TOC boilerplate.
2. Removes web CTA buttons (Sign in, check status, etc.).
3. Cuts off footer sections (Was this article helpful?, Related topics, suggestions).
4. Adds proper Markdown headings (##, ###) for major policy sections to support chunking.
5. Normalizes whitespace.
"""

import re
from pathlib import Path

DATA_DIR = Path("data/ecommerce-crawled-final")

STARTING_SENTENCES = {
    "ebay-buyer-return-shipping.md": "There are several ways you can send an item back to the seller.",
    "ebay-buyer-return-refund.md": "If you've changed your mind about an item you bought or there's something wrong with it, you can request a return.",
    "ebay-seller-protections.md": "When you sell on eBay, we protect you from abusive buying behavior and from events outside your control.",
    "ebay-seller-standards.md": "Our seller performance requirements are intended to help ensure that buyers have a great experience on eBay.",
    "ebay-buyer-money-back-guarantee.md": "eBay Money Back Guarantee covers most transactions on eBay.",
}


def clean_text_common(text: str) -> str:
    # Remove UI tooltips and web link markers
    text = text.replace(" - opens in new window or tab", "")
    text = text.replace("To improve your experience, please sign into your account.", "")

    # Remove standalone UI lines
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped in {
            "Sign in",
            "Check the status of my request",
            "View Seller Dashboard",
            "Print an eBay return label",
            "Open a return request",
        } and len(lines) > 0 and not lines[-1].startswith("#"):
            continue
        lines.append(line)
    text = "\n".join(lines)

    # Cut off footers
    footer_markers = [
        "Was this article helpful for you?",
        "Related help topics",
        "Helpful links\n\nSeller protections",
    ]
    for marker in footer_markers:
        if marker in text:
            text = text.split(marker)[0].strip()

    return text


def strip_header_boilerplate(body: str, filename: str) -> str:
    start_sent = STARTING_SENTENCES.get(filename)
    if not start_sent or start_sent not in body:
        return body

    title_match = re.match(r"^(# [^\n]+)\n+", body)
    if not title_match:
        return body

    title = title_match.group(1)
    actual_content = body[body.index(start_sent):]
    return f"{title}\n\n{actual_content}"


def process_buyer_return_shipping(body: str) -> str:
    h2s = [
        "Who pays for return shipping?",
        "How to print an eBay return shipping label",
        "Adding tracking to your return",
        "If the seller is paying for return shipping",
        "If you're paying for return shipping",
        "Other ways to send the item back",
        "Top Takeaway",
    ]
    for h in h2s:
        body = re.sub(rf"(?m)^{re.escape(h)}\s*$", f"## {h}", body)

    h3s = [
        "Return shipping costs when you use an eBay label",
        "Examples of alternative shipping arrangements",
    ]
    for h in h3s:
        body = re.sub(rf"(?m)^{re.escape(h)}\s*$", f"### {h}", body)

    return body


def process_buyer_return_refund(body: str) -> str:
    # Remove initial quick tip button block
    body = re.sub(
        r"Quick tip\s*\n+After you've opened a return request, you can check the status at any time by selecting the button below\.\s*\n+",
        "",
        body,
    )

    h2s = [
        "Faster refunds",
        "Open a return request",
        "How the seller may respond to your request",
        "Send the item back",
        "Get your refund",
        "Ask eBay to step in and help",
        "Close a return request",
        "Misuse of returns",
        "Top Takeaway",
    ]
    for h in h2s:
        body = re.sub(rf"(?m)^{re.escape(h)}\s*$", f"## {h}", body)

    h3s = [
        "More info on when you can return an item",
        "How to request a return through My eBay",
        "How to return multiple items",
        "You changed your mind about an item",
        "Your item didn't match the listing, or it arrived faulty or damaged",
        "Why was my refund less than the amount I paid?",
        "How do refunds work for items shipped through eBay International Shipping?",
    ]
    for h in h3s:
        body = re.sub(rf"(?m)^{re.escape(h)}\s*$", f"### {h}", body)

    return body


def process_seller_protections(body: str) -> str:
    h2s = [
        "Frequently Asked Questions",
        "Protections for Top Rated Sellers",
        "Protections for all sellers",
        "Events outside your control",
        "Other protections",
        "Eligibility for protections",
    ]
    for h in h2s:
        body = re.sub(rf"(?m)^{re.escape(h)}\s*$", f"## {h}", body)

    h3s = [
        "A buyer falsely claims an item was not as described",
        "An item is returned after it was used or damaged by the buyer",
        "Abusive buying activity",
        "A buyer retracted their bid or didn't pay",
        "A buyer demanded something not offered in the original listing",
        "An item arrived late but tracking shows that you shipped on time",
        "eBay International Shipping",
        "International carrier issues",
        "Severe weather or carrier disruptions caused the item to arrive late",
        "Seller performance standards",
        "Fair performance evaluation",
        "eBay Top Rated Seller grace period",
        "eBay Money Back Guarantee requests",
        "If a buyer reports that an item hasn't arrived",
        "If a buyer doesn't ship a return",
        "Duplicate claims",
        "eBay Guaranteed Fit",
        "Protections for payment disputes",
    ]
    for h in h3s:
        body = re.sub(rf"(?m)^{re.escape(h)}\s*$", f"### {h}", body)

    return body


def process_seller_standards(body: str) -> str:
    parts = body.split("Calculation examples")
    first_part = parts[0]
    rest_part = "Calculation examples" + parts[1] if len(parts) > 1 else ""

    h2s_first = [
        "What is the policy?",
        "How we calculate your seller level",
        "Cases closed without seller resolution",
        "Transaction defect rate",
        "Late shipment rate",
    ]
    for h in h2s_first:
        first_part = re.sub(
            rf"(?m)^{re.escape(h)}\s*\n+(?=What this means|On the 20th|All sellers)",
            f"## {h}\n\n",
            first_part,
        )

    first_part = re.sub(
        r"(work out your:\s*\n+)(Cases closed without seller resolution\s*\n+)(Transaction defect rate\s*\n+)(Late shipment rate)",
        r"\1- Cases closed without seller resolution\n- Transaction defect rate\n- Late shipment rate",
        first_part,
    )

    h2s_rest = [
        "Calculation examples",
        "What happens if you are Below Standard",
        "Fair evaluation, seller protections and appeals",
    ]
    for h in h2s_rest:
        rest_part = re.sub(rf"(?m)^{re.escape(h)}\s*$", f"## {h}", rest_part)

    h3s_rest = [
        "Fair evaluation",
        "Seller protections",
        "Appeals",
    ]
    for h in h3s_rest:
        rest_part = re.sub(rf"(?m)^{re.escape(h)}\s*$", f"### {h}", rest_part)

    return first_part + rest_part


def process_buyer_money_back_guarantee(body: str) -> str:
    body = re.sub(
        r"Actions and timeframes when the buyer doesn't receive an item\s*\n+"
        r"Deciding the outcome when the buyer doesn't receive an item\s*\n+"
        r"Exclusions and special coverage when the buyer doesn't receive an item\s*\n+",
        "",
        body,
    )
    body = re.sub(
        r"Actions and timeframes when the item received by the buyer doesn't match the listing\s*\n+"
        r"Deciding the outcome when the item received by the buyer doesn't match the listing\s*\n+"
        r"Exclusions and special coverage when the item received by the buyer doesn't match the listing\s*\n+",
        "",
        body,
    )

    h2s = [
        "Coverage, eligibility requirements, and exclusions",
        "When the buyer doesn't receive an item",
        "When the item received by the buyer doesn't match the listing",
        "When the seller doesn't fulfill their return policy or another agreement",
        "Return requirements and return shipping",
        "Appeals",
        "Refunds, reimbursements, and processing errors",
    ]
    for h in h2s:
        body = re.sub(rf"(?m)^{re.escape(h)}\s*$", f"## {h}", body)

    h3s = [
        "Eligible payment methods, excluded items, additional exclusions",
        "Eligible payment methods",
        "Excluded items",
        "Actions & time frames when the buyer doesn't receive an item",
        "Deciding the outcome when the buyer doesn't receive an item",
        "Exclusions and special coverage when the buyer doesn't receive an item",
        "Actions & time frames when the item received by the buyer doesn't match the listing",
        "Deciding the outcome when the item received by the buyer doesn't match the listing",
        "Exclusions and special coverage when the item received by the buyer doesn't match the listing",
        "Seller return requirements",
        "Buyer return requirements",
        "Return shipping",
        "Proof of delivery for returned items",
    ]
    for h in h3s:
        body = re.sub(rf"(?m)^{re.escape(h)}\s*$", f"### {h}", body)

    return body


PROCESSORS = {
    "ebay-buyer-return-shipping.md": process_buyer_return_shipping,
    "ebay-buyer-return-refund.md": process_buyer_return_refund,
    "ebay-seller-protections.md": process_seller_protections,
    "ebay-seller-standards.md": process_seller_standards,
    "ebay-buyer-money-back-guarantee.md": process_buyer_money_back_guarantee,
}


def clean_file(file_path: Path):
    raw_content = file_path.read_text(encoding="utf-8")
    parts = raw_content.split("---", 2)
    if len(parts) < 3:
        return

    frontmatter = f"---{parts[1]}---\n\n"
    body = parts[2].strip()

    # 1. Strip top header boilerplate
    body = strip_header_boilerplate(body, file_path.name)

    # 2. Common cleanups
    body = clean_text_common(body)

    # 3. File-specific heading formatting
    processor = PROCESSORS.get(file_path.name)
    if processor:
        body = processor(body)

    # 4. Remove any duplicate level-2 or level-3 markers if already marked
    body = re.sub(r"^#+ (##+)", r"\1", body, flags=re.MULTILINE)

    # 5. Normalize whitespace
    body = re.sub(r"[ \t]+$", "", body, flags=re.MULTILINE)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()

    result = frontmatter + body + "\n"
    file_path.write_text(result, encoding="utf-8")
    print(f"Cleaned {file_path.name}: {len(result)} chars")


def main():
    md_files = sorted(DATA_DIR.glob("*.md"))
    print(f"Cleaning {len(md_files)} files in {DATA_DIR}...")
    for f in md_files:
        clean_file(f)
    print("Done!")


if __name__ == "__main__":
    main()
