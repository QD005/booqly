import requests
from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class BaseProductService(ABC):
    @abstractmethod
    def search(self, query: str, filters: Optional[dict] = None) -> List[Dict]:
        pass


class RainforestAPIProductService(BaseProductService):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.rainforestapi.com/request"

    def search(self, query: str, filters: Optional[dict] = None) -> List[Dict]:
        params = {
            "api_key": self.api_key,
            "type": "search",
            "amazon_domain": "amazon.com",
            "search_term": query,
            "output": "json",
        }
        if filters:
            params.update(filters)
        try:
            data = requests.get(self.base_url, params=params, timeout=15).json()
            products = []
            for item in data.get("search_results", [])[:3]:
                price_raw = item.get("price", {})
                price = price_raw.get("raw", "N/A")
                if price == "N/A" and "value" in price_raw:
                    price = f"${price_raw['value']}"
                image = item.get("image") or (item.get("images", [])[0] if item.get("images") else None)
                products.append({
                    "id": item.get("asin", f"rf_{len(products)}"),
                    "name": item.get("title", "Unknown"),
                    "price": price,
                    "rating": item.get("rating"),
                    "image": image,
                    "url": item.get("link"),
                    "features": item.get("feature_bullets", [])[:3],
                })
            return products
        except Exception as e:
            print(f"Rainforest error: {e}")
            return []


class MockProductService(BaseProductService):
    IMAGE_MAP = {
        "refrigerator": [
            "https://images.unsplash.com/photo-1571175445120-20c7f3a1176e?w=400",
            "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=400",
            "https://images.unsplash.com/photo-1584568694244-14fbdf83bd30?w=400",
        ],
        "fridge": [
            "https://images.unsplash.com/photo-1571175445120-20c7f3a1176e?w=400",
            "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=400",
            "https://images.unsplash.com/photo-1584568694244-14fbdf83bd30?w=400",
        ],
        "laptop": [
            "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=400",
            "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400",
            "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=400",
        ],
        "gaming laptop": [
            "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=400",
            "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400",
            "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=400",
        ],
        "headphone": [
            "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400",
            "https://images.unsplash.com/photo-1583394838336-acd977736f90?w=400",
            "https://images.unsplash.com/photo-1484704849700-f032a568e944?w=400",
        ],
        "phone": [
            "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=400",
            "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400",
            "https://images.unsplash.com/photo-1580910051074-3eb694886505?w=400",
        ],
        "watch": [
            "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400",
            "https://images.unsplash.com/photo-1524592094714-0f0654e20314?w=400",
            "https://images.unsplash.com/photo-1542496658-e33a6d0d41f8?w=400",
        ],
        "shoe": [
            "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400",
            "https://images.unsplash.com/photo-1549298916-b41d501d3772?w=400",
            "https://images.unsplash.com/photo-1600185365926-3a2ce3cdb9eb?w=400",
        ],
        "camera": [
            "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=400",
            "https://images.unsplash.com/photo-1502920917128-1aa500764cbd?w=400",
            "https://images.unsplash.com/photo-1519183071298-a2962feb14f4?w=400",
        ],
    }

    FALLBACK = [
        "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=400",
        "https://images.unsplash.com/photo-1557821552-17105176677c?w=400",
        "https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?w=400",
    ]

    def _get_images(self, query: str) -> list:
        q = query.lower()
        for k, v in self.IMAGE_MAP.items():
            if k in q:
                return v
        return self.FALLBACK

    def search(self, query: str, filters: Optional[dict] = None) -> List[Dict]:
        clean = query.replace("I want a ", "").replace("I need a ", "").replace("Find me a ", "").replace("Show me ", "").strip()
        imgs = self._get_images(query)
        return [
            {"id": "DEMO001", "name": f"Premium {clean.title()} — Pro Series X1", "price": "$899.99", "rating": 4.7,
             "image": imgs[0], "url": "https://www.amazon.com", "features": ["Energy Star Certified", "Smart WiFi", "5-Year Warranty"]},
            {"id": "DEMO002", "name": f"Essential {clean.title()} — Value Model E2", "price": "$449.99", "rating": 4.3,
             "image": imgs[1] if len(imgs) > 1 else imgs[0], "url": "https://www.amazon.com", "features": ["Compact Design", "Low Power", "Easy Install"]},
            {"id": "DEMO003", "name": f"Professional {clean.title()} — Commercial Grade", "price": "$1,299.99", "rating": 4.9,
             "image": imgs[2] if len(imgs) > 2 else imgs[0], "url": "https://www.amazon.com", "features": ["Commercial Build", "Advanced Tech", "10-Year Warranty"]},
        ]