import logging
import re


logger = logging.getLogger("PING-MANAGER")


def lego_retirement_ping_data(db, ping_data, document):
    try:
        sku = document.get("sku")
        # Links field is alway at the botton which is why -1 is used
        links = ping_data.get("fields")[-1].get("value")
        links = f"**| {links}"
        end = " |**"

        # Add ebay mean price
        ebay_filter = {"website": "eBay", "sku": sku}
        ebay_product = db.fetch_product(ebay_filter)
        if ebay_product is not None:
            ebay_field = {
                "name": "**eBay Mean Price**",
                "value": f"£{ebay_product.get('mean-price')}"
            }
            ping_data["fields"].insert(-1, ebay_field)

        if (document.get("website") == "Amazon"):
            keepa_link = f"https://keepa.com/#product/2-{extract_amazon_asin(document.get('link'))}" 
            links += f" | [Keepa]({keepa_link})"
        else:
            filter = {"sku": sku, "website": "Amazon"}
            amazon_link = db.fetch_product(filter).get("link")
            if amazon_link is not None:
                links += f" | [Amazon]({amazon_link})"
                keepa_link = f"https://keepa.com/#product/2-{extract_amazon_asin(amazon_link)}" 
                links += f" | [Keepa]({keepa_link})"

        # Add lego link
        lego_link = "https://www.lego.com/en-gb/search?q=" + sku
        links += f" | [Lego]({lego_link})"

        links += end
        ping_data["fields"][-1]["value"] = links

        return ping_data
    
    except Exception as error:
        logger.error(f"{document.get('website')}", error)


def extract_amazon_asin(url):
    match = re.search(r'/dp/([A-Z0-9]{10})', url)
    if match:
        return match.group(1)
    
    return ''