import requests


BROWSE_API = "https://api.ebay.com/buy/browse/v1/item_summary/search"
OAUTH_URL  = "https://api.ebay.com/identity/v1/oauth2/token"
PAGE_SIZE  = 200
MAX_PAGES  = 15


class EbayAPIClient:
    def __init__(self, app_id: str, cert_id: str = ""):
        """
        app_id: eBay Production App ID (Client ID) from developer.ebay.com
        cert_id: eBay Production Cert ID (Client Secret) from developer.ebay.com
        """
        self.app_id = app_id.strip()
        self.cert_id = cert_id.strip()
        self._token = None

    def _get_token(self):
        """Get an OAuth application token using client_credentials grant."""
        if self._token:
            return self._token
            
        auth_pair = (self.app_id, self.cert_id) if self.cert_id else (self.app_id, "")
        resp = requests.post(
            OAUTH_URL,
            auth=auth_pair,
            data={
                "grant_type": "client_credentials",
                "scope": "https://api.ebay.com/oauth/api_scope"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15
        )
        resp.raise_for_status()
        self._token = resp.json().get("access_token", "")
        return self._token

    def search(self, store_url: str, include_term: str,
               exclude_terms: list[str] = None,
               condition: str = "all") -> list[dict]:
        """Search a seller's store via the eBay Browse API."""
        seller = self._seller_from_url(store_url)
        exclude_terms = exclude_terms or []
        items  = []
        offset = 0

        # Build clean keyword query with quoted multi-word exclusions
        nkw_parts = [include_term]
        for ex in exclude_terms:
            ex_str = ex.strip().strip('"')
            if ex_str and ex_str.lower() not in include_term.lower():
                if " " in ex_str:
                    nkw_parts.append(f'-"{ex_str}"')
                else:
                    nkw_parts.append(f"-{ex_str}")
        query = " ".join(nkw_parts)

        try:
            token = self._get_token()
        except Exception as e:
            raise RuntimeError(f"Failed to authenticate eBay API: {e}")

        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
        }

        while offset // PAGE_SIZE < MAX_PAGES:
            filter_parts = []
            if seller:
                filter_parts.append(f"sellers:{{{seller}}}")
            if condition == "new":
                filter_parts.append("conditions:{NEW}")
            elif condition == "used":
                filter_parts.append("conditions:{USED}")

            params = {
                "q":             query,
                "limit":         PAGE_SIZE,
                "offset":        offset,
                "fieldgroups":   "EXTENDED",
            }
            if filter_parts:
                params["filter"] = ",".join(filter_parts)

            try:
                resp = requests.get(BROWSE_API, headers=headers,
                                    params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                raise RuntimeError(f"eBay API error: {e}")

            summaries = data.get("itemSummaries", [])
            if not summaries:
                break

            for item in summaries:
                image_url = ""
                if item.get("image"):
                    image_url = item["image"].get("imageUrl", "")
                elif item.get("thumbnailImages"):
                    image_url = item["thumbnailImages"][0].get("imageUrl", "")

                price = ""
                if item.get("price"):
                    price = f"{item['price'].get('currency','')} {item['price'].get('value','')}"

                item_loc = item.get("itemLocation", {})
                country = item_loc.get("country", "")
                postal = item_loc.get("postalCode", "")
                loc_str = country
                if country and postal:
                    loc_str = f"{country} ({postal})"

                items.append({
                    "title":     item.get("title", ""),
                    "url":       item.get("itemWebUrl", ""),
                    "item_id":   item.get("itemId", ""),
                    "price":     price,
                    "image_url": image_url,
                    "seller":    item.get("seller", {}).get("username", seller),
                    "location":  loc_str,
                })

            total = data.get("total", 0)
            offset += PAGE_SIZE
            if offset >= total:
                break

        return items

    def _seller_from_url(self, url: str) -> str:
        if not url:
            return ""
        url = url.strip().rstrip("/")
        for prefix in ["/str/", "/usr/", "/seller/"]:
            if prefix in url.lower():
                return url.lower().split(prefix)[-1].split("/")[0].split("?")[0]
        if not url.startswith("http"):
            return url
        return url.split("/")[-1].split("?")[0]
