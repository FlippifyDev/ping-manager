import pyshorteners
import logging
import re


logger = logging.getLogger("PING-MANAGER")

type_tiny = pyshorteners.Shortener()


def ping_data_retiring_sets(db, ping_data, document):
    try:
        sku = document.get("sku")
        # Links field is alway at the botton which is why -1 is used
        links = ping_data.get("fields")[-1].get("value")
        links = f"**| {links}"
        end = " |**"

        # Add ebay mean price and link
        ebay_filter = {"website": "eBay", "sku": sku}
        ebay_product = db.fetch_retiring_sets_product(ebay_filter)
        if ebay_product is not None:
            ebay_field = {
                "name": "**eBay Prices**",
                "value": f"Mean £{ebay_product.get('mean-price')} | Max £{ebay_product.get('max-price')}"
            }
            ping_data["fields"].insert(-2, ebay_field)

            ebay_link = ebay_product.get("link")
            if ebay_link:
                # Perform the replacements outside the f-string
                ebay_link_replaced = ebay_link.replace("\u00A0", "+").replace(' ', '+')
                # Construct the f-string
                links += f" | [eBay]({ebay_link_replaced})"
        
        # Add the Keepa link
        if (document.get("website") == "Amazon"):
            amazon_link = document.get("link")
            if amazon_link:
                keepa_link = f"https://keepa.com/#product/2-{extract_amazon_asin(amazon_link)}" 
                links += f" | [Keepa]({keepa_link})"

        else:
            filter = {"sku": sku, "website": "Amazon"}
            amazon_prod = db.fetch_product(filter)
            if amazon_prod:
                amazon_link = amazon_prod.get("link")
                if amazon_link is not None:
                    keepa_link = f"https://keepa.com/#product/2-{extract_amazon_asin(amazon_link)}" 
                    amazon_link = type_tiny.tinyurl.short(amazon_prod.get("link"))
                    links += f" | [Amazon]({amazon_link})"
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