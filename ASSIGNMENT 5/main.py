from fastapi import FastAPI, Query, Response, status
from pydantic import BaseModel, Field
from typing import Optional, List
from fastapi import HTTPException
import math

app = FastAPI()

products = [

    {'id': 1, 'name': 'Wireless Mouse', 'price': 499,  'category': 'Electronics', 'in_stock': True },
    {'id': 2, 'name': 'Notebook', 'price':  99,  'category': 'Stationery',  'in_stock': True },
    {'id': 3, 'name': 'USB Hub', 'price': 799, 'category': 'Electronics', 'in_stock': False},
    {'id': 4, 'name': 'Pen Set',  'price':  49, 'category': 'Stationery',  'in_stock': True }

]

@app.get('/')

def home():

    return {'message': 'Welcome to our E-commerce API'}

@app.get('/products')

def get_all_products():

    return {'products': products, 
            'total': len(products)}


# Add a Category Filter Endpoint
@app.get("/products/category/{category_name}")
def get_products_by_category(category_name: str):
    filtered = [p for p in products if p["category"].lower() == category_name.lower()]

    if not filtered:
        return {"error": "No products found in this category"}

    return {
        "category": category_name,
        "products": filtered,
        "count": len(filtered)
    }


# Only in-stock products
@app.get("/products/instock")
def get_instock_products():
    instock = [p for p in products if p["in_stock"]]

    return {
        "in_stock_products": instock,
        "count": len(instock)
    }


# Build a Store Info Endpoint
@app.get("/store/summary")
def store_summary():
    total = len(products)
    instock = len([p for p in products if p["in_stock"]])
    outstock = total - instock

    categories = list(set(p["category"] for p in products))

    return {
        "store_name": "My E-commerce Store",
        "total_products": total,
        "in_stock": instock,
        "out_of_stock": outstock,
        "categories": categories
    }


# Search Products by Name
@app.get("/products/search/{keyword}")
def search_products(keyword: str):
    results = [
        p for p in products
        if keyword.lower() in p["name"].lower()
    ]

    if not results:
        return {"message": "No products matched your search"}

    return {
        "matched_products": results,
        "count": len(results)
    }


# Bonus — Cheapest & Most Expensive product
@app.get("/products/deals")
def product_deals():
    cheapest = min(products, key=lambda x: x["price"])
    expensive = max(products, key=lambda x: x["price"])

    return {
        "best_deal": cheapest,
        "premium_pick": expensive
    }

# Filter Products by Minimum Price

@app.get("/products/filter")
def filter_products(
    min_price: int = Query(None, description="Minimum price"),
    max_price: int = Query(None, description="Maximum price"),
    category: Optional[str] = Query(None, description="Category filter")
):
    result = products

    if min_price is not None:
        result = [p for p in result if p["price"] >= min_price]

    if max_price is not None:
        result = [p for p in result if p["price"] <= max_price]

    if category is not None:
        result = [p for p in result if p["category"] == category]

    return result


# Get Only the Price of a Product

@app.get("/products/{product_id}/price")
def get_product_price(product_id: int):
    for product in products:
        if product["id"] == product_id:
            return {"name": product["name"], "price": product["price"]}
    return {"error": "Product not found"}

# Accept Customer Feedback

class CustomerFeedback(BaseModel):
    customer_name: str            = Field(..., min_length=2, max_length=100)
    product_id:   int            = Field(..., gt=0)
    rating:       int            = Field(..., ge=1, le=5)
    comment:      Optional[str]  = Field(None, max_length=300)

feedback = []

@app.post("/feedback")
def submit_feedback(data: CustomerFeedback):
    feedback.append(data.dict())
    return {
        "message":        "Feedback submitted successfully",
        "feedback":       data.dict(),
        "total_feedback": len(feedback),
    }
    
# Build a Product Summary Dashboard

@app.get("/products/summary")
def product_summary():

    in_stock = [p for p in products if p["in_stock"]]
    out_stock = [p for p in products if not p["in_stock"]]

    expensive = max(products, key=lambda p: p["price"])
    cheapest = min(products, key=lambda p: p["price"])

    categories = list(set(p["category"] for p in products))

    return {
        "total_products": len(products),
        "in_stock_count": len(in_stock),
        "out_of_stock_count": len(out_stock),
        "most_expensive": {
            "name": expensive["name"],
            "price": expensive["price"]
        },
        "cheapest": {
            "name": cheapest["name"],
            "price": cheapest["price"]
        },
        "categories": categories
    }
    
# Validate & Place a Bulk Order

class OrderItem(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity:   int = Field(..., gt=0, le=50)

class BulkOrder(BaseModel):
    company_name:  str           = Field(..., min_length=2)
    contact_email: str           = Field(..., min_length=5)
    items:         List[OrderItem] = Field(..., min_items=1)

@app.post("/orders/bulk")
def place_bulk_order(order: BulkOrder):

    confirmed = []
    failed = []
    grand_total = 0

    for item in order.items:

        product = next((p for p in products if p["id"] == item.product_id), None)

        if not product:
            failed.append({
                "product_id": item.product_id,
                "reason": "Product not found"
            })

        elif not product["in_stock"]:
            failed.append({
                "product_id": item.product_id,
                "reason": f"{product['name']} is out of stock"
            })

        else:
            subtotal = product["price"] * item.quantity
            grand_total += subtotal

            confirmed.append({
                "product": product["name"],
                "qty": item.quantity,
                "subtotal": subtotal
            })

    return {
        "company": order.company_name,
        "confirmed": confirmed,
        "failed": failed,
        "grand_total": grand_total
    }
    
# Orders list to store all orders
orders = []
order_counter = 1  # simple ID generator

class OrderRequest(BaseModel):
    customer_name: str = Field(..., min_length=2)
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)

@app.post("/orders")
def place_order(order: OrderRequest):
    global order_counter

    product = next((p for p in products if p["id"] == order.product_id), None)

    if not product:
        return {"error": "Product not found"}

    if not product.get("in_stock", True):  # safer
        return {"error": f"{product['name']} is out of stock"}

    total_price = product["price"] * order.quantity

    new_order = {
        "order_id": order_counter,
        "customer_name": order.customer_name,
        "product": product["name"],
        "qty": order.quantity,
        "total": total_price,
        "status": "pending"
    }

    orders.append(new_order)
    order_counter += 1

    return {"message": "Order placed", "order": new_order}

# SEARCH ORDERS
@app.get("/orders/search")
def search_orders(customer_name: str):

    result = [
        order for order in orders
        if customer_name.lower() in order["customer_name"].lower()
    ]

    if not result:
        return {"message": "No orders found for this customer"}

    return {
        "customer_name": customer_name,
        "total_found": len(result),
        "orders": result
    }

# PATCH to confirm:
@app.patch("/orders/{order_id}/confirm")
def confirm_order(order_id: int):
    for order in orders:
        if order["order_id"] == order_id:
            order["status"] = "confirmed"
            return {"message": "Order confirmed", "order": order}
    return {"error": "Order not found"}

@app.get("/products/audit")
def audit_products():
    total_products = len(products)
    in_stock_products = [p for p in products if p["in_stock"]]
    out_of_stock_products = [p for p in products if not p["in_stock"]]
    in_stock_count = len(in_stock_products)
    out_of_stock_names = [p["name"] for p in out_of_stock_products]
    total_stock_value = sum(p["price"] * 10 for p in in_stock_products)
    most_expensive = max(products, key=lambda x: x["price"])
    return {
        "total_products": total_products,
        "in_stock_count": in_stock_count,
        "out_of_stock_names": out_of_stock_names,
        "total_stock_value": total_stock_value,
        "most_expensive": {
            "name": most_expensive["name"],
            "price": most_expensive["price"]
        }
    }

@app.put("/products/discount")
def discount_products(category: str, discount_percent: int):
    updated = []
    for p in products:
        if p["category"].lower() == category.lower():
            new_price = int(p["price"] * (1 - discount_percent / 100))
            p["price"] = new_price
            updated.append({"name": p["name"], "new_price": new_price})
    if not updated:
        return {"message": "No products found in this category"}
    return {
        "updated_count": len(updated),
        "products": updated
    }
    
# Product CRUD

class NewProduct(BaseModel):
    name: str = Field(..., min_length=2)
    price: int = Field(..., gt=0)
    category: str = Field(..., min_length=2)
    in_stock: bool

def find_product(product_id: int):
    for product in products:
        if product["id"] == product_id:
            return product
    return None

@app.post('/products')
def add_product(new_product: NewProduct, response: Response):
    for p in products:
        if p["name"].lower() == new_product.name.lower():
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {"error": "Product with this name already exists"}
    next_id = max(p['id'] for p in products) + 1
    product = {
        'id': next_id,
        'name': new_product.name,
        'price': new_product.price,
        'category': new_product.category,
        'in_stock': new_product.in_stock
    }
    products.append(product)
    response.status_code = status.HTTP_201_CREATED
    return {"message": "Product added", "product": product}

@app.put('/products/{product_id}')
def update_product(
    product_id: int,
    response: Response,
    in_stock: bool = Query(None),
    price: int = Query(None),
):
    product = find_product(product_id)
    if not product:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {'error': 'Product not found'}
    if in_stock is not None:
        product['in_stock'] = in_stock
    if price is not None:
        product['price'] = price
    return {'message': 'Product updated', 'product': product}

@app.delete('/products/{product_id}')
def delete_product(product_id: int, response: Response):
    product = find_product(product_id)
    if not product:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {'error': 'Product not found'}
    products.remove(product)
    return {'message': f"Product '{product['name']}' deleted"}

# SORT PRODUCTS

@app.get("/products/sort")
def sort_products(sort_by: str = "price", order: str = "asc"):
    if sort_by not in ["price", "name"]:
        raise HTTPException(status_code=400, detail="sort_by must be 'price' or 'name'")

    # Sorting logic
    reverse = True if order == "desc" else False
    sorted_products = sorted(products, key=lambda x: x[sort_by], reverse=reverse)

    return {
        "sort_by": sort_by,
        "order": order,
        "products": sorted_products
    }

# PAGINATION (PRODUCTS)
@app.get("/products/page")
def paginate_products(page: int = 1, limit: int = 2):

    start = (page - 1) * limit
    end = start + limit

    total_pages = math.ceil(len(products) / limit)

    return {
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "products": products[start:end]
    }
    
# BONUS - PAGINATION (ORDERS)
@app.get("/orders/page")
def paginate_orders(page: int = 1, limit: int = 3):

    start = (page - 1) * limit
    end = start + limit

    total_pages = math.ceil(len(orders) / limit)

    return {
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "orders": orders[start:end]
    }

# Bonus - Order Status Tracker
@app.get("/orders/{order_id}")
def get_order(order_id: int):
    for order in orders:
        if order["order_id"] == order_id:
            return {"order": order}
    return {"error": "Order not found"}

# SORT BY CATEGORY THEN PRICE
@app.get("/products/sort-by-category")
def sort_by_category():

    sorted_products = sorted(products, key=lambda x: (x["category"], x["price"]))

    return {"products": sorted_products}

# SEARCH + SORT + PAGINATE
@app.get("/products/browse")
def browse_products(
    keyword: Optional[str] = None,
    sort_by: str = "price",
    order: str = "asc",
    page: int = 1,
    limit: int = 4
):

    # Filter
    filtered = products
    if keyword:
        filtered = [
            p for p in products
            if keyword.lower() in p["name"].lower()
        ]

    # Sort
    if sort_by not in ["price", "name"]:
        raise HTTPException(status_code=400, detail="Invalid sort_by")

    reverse = True if order == "desc" else False
    filtered = sorted(filtered, key=lambda x: x[sort_by], reverse=reverse)

    # Paginate
    start = (page - 1) * limit
    end = start + limit
    total_pages = math.ceil(len(filtered) / limit)

    return {
        "keyword": keyword,
        "sort_by": sort_by,
        "order": order,
        "page": page,
        "limit": limit,
        "total_found": len(filtered),
        "total_pages": total_pages,
        "products": filtered[start:end]
    }

@app.get("/products/{product_id}")
def get_product(product_id: int):
    product = find_product(product_id)
    if not product:
        return {"error": "Product not found"}
    return {"product": product}
