from datetime import datetime, timezone

import pyshorteners
import logging
import re


logger = logging.getLogger("PING-MANAGER")

type_tiny = pyshorteners.Shortener()



def handle_should_send_ping(db, before, after):
    try:
        scraper_type = after.get("type")

        # Check if the price has changed and stock is available
        if should_send_ping_default(before, after, scraper_type=scraper_type) is False:
            return False
        
        if scraper_type == "Electronics":
            return should_send_ping_electronics(db, before, after, minimum_sale=0.40)
        elif scraper_type == "Deal-Watch-UK":
            # When a document is added to the deal-watch collection then it must be sent
            return True
        elif scraper_type == "Restock-Info":
            return should_send_ping_restock_info(after)  
        elif scraper_type == "Sneaker-Release-Info":
            return should_send_ping_sneaker_release_info(after)  
        elif scraper_type == "Retiring-Sets-Deals":
            return should_send_ping_retiring_sets(before, after, minimum_sale=0.20)
        else:
            return should_send_ping_default(before, after, minimum_sale=0.15)

    except Exception as error:
        logger.error(error)



def should_send_ping_default(before, after, minimum_sale=0, scraper_type=None):
    try:
        if scraper_type == "Sneaker-Release-Info":
            return True
        
        # Let the individual ping handlers handle when there is no prvious price
        if before is None:
            return True
        # Check conditions for sending a ping
        after_price = after.get('price')
        if after_price is None:
            return False
        
        before_price = before.get('price') 
        # Use after_price + 1 if no before_price
        if before_price is None:
            before_price = after_price + 1
        # Before document
        before_stock_available = before.get('stock_available', False)   
        # After document
        after_stock_available = after.get('stock_available')

        if scraper_type not in ["Restock-Info", "Deal-Watch-UK"]:
            after_rrp = after.get('rrp')
            if after_rrp is None:
                return False
            sale = 1-(after_price / after_rrp)
        else:
            sale = 0
        
        if sale >= minimum_sale:
            if after_price < before_price and after_stock_available:
                return True
            elif after_stock_available and not before_stock_available:
                return True
        return False
    
    except Exception as error:
        logger.error(error)



def should_send_ping_sneaker_release_info(after):
    return after.get("send_ping")


def should_send_ping_restock_info(after, minimum_roi=0.15):
    sold_last_7_days = after["sold_last_7_days"]
    if sold_last_7_days is None:
        return False
    if sold_last_7_days <= 2:
        return False
    
    roi = (after["ebay_mean_price"] - after["price"]) / after["price"]
    if roi >= minimum_roi:
        return True
    return False
    


def should_send_ping_electronics(db, before, after, minimum_sale, required_roi=0.10, minimum_profit=10):
    try:
        # Get the ebay document related to this product
        ebay_product_name = before.get('product_name')
        ebay_filter = {"website": "eBay", "region": before.get("region"), "product_name": ebay_product_name}
        ebay_product = db.fetch_product(ebay_filter, "ebay")

        # If the ebay product doesn't exist then send the ping by the default method
        if ebay_product is None:
            return should_send_ping_default(before, after, minimum_sale)
        
        ebay_mean_price = ebay_product.get("mean_price")
        buy_price = after.get("price")
        profit_no_fees = (ebay_mean_price-buy_price)
        if profit_no_fees <= 0:
            return False
        
        revenue = ebay_mean_price
        profit_no_fees = revenue-buy_price
        if profit_no_fees < minimum_profit:
            return False
        
        estimated_roi = (revenue-buy_price) / buy_price
        if estimated_roi < required_roi:
            return False
        
        return True

    except Exception as error:
        logger.error(error)
        return False



def should_send_ping_retiring_sets(before, after, minimum_sale):
    if before.get("website") == "Amazon":
        if before.get("sold_by_amazon") is False:
            return False
    
    return should_send_ping_default(before, after, minimum_sale)



def ping_data_restock_info(ping_data, document):
    try:
        if document.get("maxOrderQuantity") is not None:
            max_order_quantity_field = {"name": "**Max Order Quantity**", "value": document.get("maxOrderQuantity")}
            ping_data["fields"].insert(-1, max_order_quantity_field)

        if document.get("release_date") is not None:
            release_date_field = {"name": "**Release Date**", "value": document.get("release_date")}
            ping_data["fields"].insert(-1, release_date_field)

        if document.get("stock_level") == "Low Stock":
            low_stock_field = {"name": "**Stock**", "value": "Low"}
            ping_data["fields"].insert(-1, low_stock_field)

        return ping_data

    except Exception as error:
        logger.error(error)



def ping_data_electronics(db, ping_data, document):
    """
    Args:
        document: The document of the product in the database that has just been changed.
        ping_data: The embed which will be sent.
    """
    try:
        # Continue updating the documents so they start with the brand and end with the device
        # Links field is alway at the botton which is why -1 is used
        links = ping_data.get("fields")[-1].get("value").replace(document.get("website"), "Get Deal")
        links = f"**| {links}"
        end = " |**"

        ping_data, ebay_product = add_ebay_fields(db, document, ping_data)
        ping_data["description"] = f"> Profit of {round(ebay_product.get('mean_price') - document.get('price'), 2)}"

        links = add_ebay_amazon_links(db, document, ebay_product, links, document.get('product_name'), col="electronics")
        links += end
        ping_data["fields"][-1]["value"] = links

        return ping_data             

    except Exception as error:
        logger.error(error)


def ping_data_sneaker_release_info(db, ping_data, document):
    # Get the release date from the document
    release_date = document["release_date"]

    release_date_utc = release_date.astimezone(timezone.utc)
    unix_timestamp = int(release_date_utc.timestamp())
    discord_timestamp = f"<t:{unix_timestamp}:F>"

    relative_time_until_release = f"<t:{unix_timestamp}:R>"

    # Insert the release date into ping_data
    ping_data["fields"].insert(
        0,
        {
            "name": "**Time Until Release**",
            "value": relative_time_until_release 
        }
    )

    # Insert the release date into ping_data
    ping_data["fields"].insert(
        1,
        {
            "name": "**Release Date**",
            "value": discord_timestamp 
        }
    )

    db.update_product({"_id": document["_id"]}, {"$set": {"ping_sent": True, "send_ping": False}}, "sneaker-release-info")

    return ping_data


def ping_data_retiring_sets(db, ping_data, document):
    try:
        sku = document.get("sku")
        # Links field is always at the botton which is why -1 is used
        links = ping_data.get("fields")[-1].get("value")
        links = f"**| {links}"
        end = " |**"

        # Add ebay mean price and link
        ebay_filter = {"website": "eBay", "region": document.get("region"), "product_name": document.get("product_name")}
        ebay_product = db.fetch_product(ebay_filter, col="ebay")
        if ebay_product is not None:
            ebay_field = {
                "name": "**eBay Prices**",
                "value": f"Mean £{ebay_product.get('mean_price')} | Max £{ebay_product.get('max_price')}"
            }
            ping_data["fields"].insert(-2, ebay_field)
        
        links = add_ebay_amazon_links(db, document, ebay_product, links, document.get("product_name"), col="retiring-sets")

        # Add lego link
        lego_link = "https://www.lego.com/en-gb/search?q=" + sku
        links += f" | [Lego]({lego_link})"

        links += end
        ping_data["fields"][-1]["value"] = links

        return ping_data
    
    except Exception as error:
        logger.error(f"{document.get('website')}", error)



def add_ebay_amazon_links(db, document, ebay_product, links, amazon_product_name, col):
    try:
        if ebay_product is not None:
            ebay_link = ebay_product.get("link")
            if ebay_link:
                # Perform the replacements outside the f-string
                ebay_link_replaced = ebay_link.replace("\u00A0", "+").replace(' ', '+')
                # Construct the f-string
                links += f" | [eBay Sell History]({ebay_link_replaced})" 

        # Add the Keepa link
        if (document.get("website") == "Amazon"):
            amazon_link = document.get("link")
            if amazon_link:
                keepa_link = f"https://keepa.com/#product/2-{extract_amazon_asin(amazon_link)}" 
                links += f" | [Keepa]({keepa_link})"
        else:
            filter = {"product_name": amazon_product_name, "website": "Amazon", "region": document.get("region")}
            amazon_prod = db.fetch_product(filter, col)
            if amazon_prod:
                amazon_link = amazon_prod.get("link")
                if amazon_link is not None:
                    keepa_link = f"https://keepa.com/#product/2-{extract_amazon_asin(amazon_link)}" 
                    amazon_link = type_tiny.tinyurl.short(amazon_prod.get("link"))
                    links += f" | [Amazon]({amazon_link})"
                    links += f" | [Keepa]({keepa_link})"
        
        return links

    except Exception as error:
        logger.error(error)


def format_time_difference(release_date):
    """Format the time difference from now until the release date."""
    current_time = datetime.now(timezone.utc)
    time_difference = release_date - current_time

    days = time_difference.days
    hours, remainder = divmod(time_difference.seconds, 3600)
    minutes, _ = divmod(remainder, 60)

    if days > 0:
        return f"{days} day(s) and {hours} hour(s) left"
    elif hours > 0:
        return f"{hours} hour(s) and {minutes} minute(s) left"
    else:
        return f"{minutes} minute(s) left" if minutes > 0 else "Release is now!"


def add_ebay_fields(db, document, ping_data):
    try:
        ebay_product_name = document.get('product_name')

        ebay_filter = {"website": "eBay", "region": document.get("region"), "product_name": ebay_product_name, "type": document.get("type")}
        ebay_product = db.fetch_product(ebay_filter, "ebay")

        if ebay_product is None:
            ping_data["fields"][0]["inline"] = False
            del ping_data["fields"][2]
            return ping_data, None
        
        #buy_price = document.get("price")
        #sell_price = ebay_product.get("mean_price")
        #profit_12_8_percent_fees = round((sell_price*0.872) - buy_price, 2)
        #profit_3_percent_fees = round((sell_price*0.97) - buy_price, 2)

        # Add the profit fields
        """
        ping_data["fields"].insert(
            0, 
            {
                "name": "** **",
                "value": "** **",
                "inline": True
            }
        )
        ping_data["fields"].insert(
            0, 
            {
                "name": "**Profit 3% fees**",
                "value": f"£{profit_3_percent_fees}",
                "inline": True
            }
        )
        ping_data["fields"].insert(
            0, 
            {
                "name": "**Profit 12.8% fees**",
                "value": f"£{profit_12_8_percent_fees}",
                "inline": True
            }
        )
        ping_data["fields"].insert(
            0, 
            {
                "name": "** **",
                "value": "** **",
                "inline": False
            }
        )
        """


        # Add the ebay fields
        ping_data["fields"].insert(
            -1, 
            {
                "name": "**eBay Mean Price**",
                "value": f"£{ebay_product.get('mean_price')}"
            }
        )
        ping_data["fields"].insert(
            -1, 
            {
                "name": "**eBay Max Price**",
                "value": f"£{ebay_product.get('max_price')}"
            }
        )

        return ping_data, ebay_product
                
    except Exception as error:
        logger.error(error)



def extract_amazon_asin(url):
    match = re.search(r'/dp/([A-Z0-9]{10})', url)
    if match:
        return match.group(1)
    
    return ''