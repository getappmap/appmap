#!/usr/bin/env python3
"""Generate a larger synthetic AppMap to benchmark scaling behavior."""
import json
import random

random.seed(42)

CONTROLLERS = ["OrdersController", "ProductsController", "UsersController", "CartController"]
SERVICES = ["OrderProcessingService", "InventoryService", "PaymentService", "NotificationService"]
MODELS = ["Order", "Product", "User", "Cart", "LineItem", "Payment"]
MIDDLEWARE = ["ApplicationController", "AuthenticationConcern", "RateLimitConcern"]

def make_receiver(cls: str, oid: int, static: bool = False):
    if static:
        return {"name": "self", "class": "Module", "value": cls, "object_id": oid}
    return {"name": "self", "class": cls, "value": f"#<{cls}:0x{oid:016x}>", "object_id": oid}

def make_param(name: str, cls: str, val: str, oid: int):
    return {"name": name, "class": cls, "value": val, "object_id": oid}

events = []
eid = 1

def push_call(e):
    global eid
    e["id"] = eid
    e["event"] = "call"
    e["thread_id"] = 47219853920000
    events.append(e)
    result = eid
    eid += 1
    return result

def push_return(parent_id, elapsed, **kwargs):
    global eid
    e = {"id": eid, "event": "return", "parent_id": parent_id, "elapsed": elapsed}
    e.update(kwargs)
    events.append(e)
    eid += 1

# HTTP server request entry
http_call_id = push_call({
    "http_server_request": {
        "request_method": "POST",
        "path_info": "/orders",
        "normalized_path_info": "/orders",
        "protocol": "HTTP/1.1",
        "headers": {
            "host": "api.example.com",
            "content-type": "application/json",
            "authorization": "Bearer tok.abc123",
            "user-agent": "Mozilla/5.0",
            "accept": "application/json",
            "accept-encoding": "gzip, deflate",
            "content-length": "145"
        }
    },
    "message": [
        make_param("product_id", "Integer", "7", 100001),
        make_param("quantity", "Integer", "3", 100002),
        make_param("shipping_address", "String", "123 Main St, Springfield", 100003)
    ]
})

# Middleware
auth_call = push_call({
    "defined_class": "AuthenticationConcern",
    "method_id": "authenticate_user!",
    "path": "app/controllers/concerns/authentication_concern.rb",
    "lineno": 5, "static": False,
    "receiver": make_receiver("AuthenticationConcern", 200001),
    "parameters": []
})

# JWT decode SQL
jwt_sql_call = push_call({
    "sql_query": {
        "database_type": "postgresql",
        "sql": 'SELECT "users".* FROM "users" WHERE "users"."id" = $1 LIMIT $2',
        "server_version": "14.5"
    },
    "message": [make_param("binds", "Array", '["42", 1]', 200010)]
})
push_return(jwt_sql_call, 0.002341)
push_return(auth_call, 0.003892, return_value=make_param("user", "User", "#<User id: 42>", 200002))

# Rate limit check
rate_call = push_call({
    "defined_class": "RateLimitConcern",
    "method_id": "check_rate_limit!",
    "path": "app/controllers/concerns/rate_limit_concern.rb",
    "lineno": 12, "static": False,
    "receiver": make_receiver("RateLimitConcern", 200003),
    "parameters": [make_param("key", "String", "user:42:orders", 200004)]
})
push_return(rate_call, 0.000421, return_value=make_param("result", "TrueClass", "true", 2))

# Main controller
orders_ctrl = push_call({
    "defined_class": "OrdersController",
    "method_id": "create",
    "path": "app/controllers/orders_controller.rb",
    "lineno": 15, "static": False,
    "receiver": make_receiver("OrdersController", 300001),
    "parameters": []
})

# Strong params
strong_params_call = push_call({
    "defined_class": "OrdersController",
    "method_id": "order_params",
    "path": "app/controllers/orders_controller.rb",
    "lineno": 45, "static": False,
    "receiver": make_receiver("OrdersController", 300001),
    "parameters": []
})
push_return(strong_params_call, 0.000198,
            return_value=make_param("params", "ActionController::Parameters",
                                    '{"product_id"=>7, "quantity"=>3, "shipping_address"=>"123 Main St"}', 300010))

# Service call
svc_call = push_call({
    "defined_class": "OrderProcessingService",
    "method_id": "call",
    "path": "app/services/order_processing_service.rb",
    "lineno": 8, "static": False,
    "receiver": make_receiver("OrderProcessingService", 400001),
    "parameters": [
        make_param("user", "User", "#<User id: 42>", 200002),
        make_param("params", "ActionController::Parameters",
                   '{"product_id"=>7, "quantity"=>3}', 300010)
    ]
})

# Inventory check
inv_call = push_call({
    "defined_class": "InventoryService",
    "method_id": "check_availability",
    "path": "app/services/inventory_service.rb",
    "lineno": 22, "static": False,
    "receiver": make_receiver("InventoryService", 500001),
    "parameters": [
        make_param("product_id", "Integer", "7", 100001),
        make_param("quantity", "Integer", "3", 100002)
    ]
})

inv_sql = push_call({
    "sql_query": {
        "database_type": "postgresql",
        "sql": 'SELECT "products"."id", "products"."stock_count" FROM "products" WHERE "products"."id" = $1 FOR UPDATE',
        "server_version": "14.5"
    },
    "message": [make_param("binds", "Array", '["7"]', 500010)]
})
push_return(inv_sql, 0.004123)
push_return(inv_call, 0.005012, return_value=make_param("available", "TrueClass", "true", 2))

# Product model
product_find = push_call({
    "defined_class": "Product",
    "method_id": "find",
    "path": "app/models/product.rb",
    "lineno": 5, "static": True,
    "receiver": make_receiver("Product", 600001, static=True),
    "parameters": [make_param("id", "Integer", "7", 100001)]
})
product_sql = push_call({
    "sql_query": {
        "database_type": "postgresql",
        "sql": 'SELECT "products".* FROM "products" WHERE "products"."id" = $1 LIMIT $2',
        "server_version": "14.5"
    },
    "message": [make_param("binds", "Array", '["7", 1]', 600010)]
})
push_return(product_sql, 0.001892)
push_return(product_find, 0.002541, return_value=make_param("product", "Product",
    '#<Product id: 7, name: "Widget Pro", price: 29.99, stock_count: 150>', 600002))

# Price calculation
price_call = push_call({
    "defined_class": "OrderProcessingService",
    "method_id": "calculate_total",
    "path": "app/services/order_processing_service.rb",
    "lineno": 67, "static": False,
    "receiver": make_receiver("OrderProcessingService", 400001),
    "parameters": [
        make_param("product", "Product", '#<Product id: 7, price: 29.99>', 600002),
        make_param("quantity", "Integer", "3", 100002)
    ]
})

# Tax service call
tax_call = push_call({
    "defined_class": "TaxCalculator",
    "method_id": "compute",
    "path": "lib/tax_calculator.rb",
    "lineno": 18, "static": True,
    "receiver": make_receiver("TaxCalculator", 700001, static=True),
    "parameters": [
        make_param("subtotal", "BigDecimal", "89.97", 700010),
        make_param("state", "String", "CA", 700011)
    ]
})
push_return(tax_call, 0.000312, return_value=make_param("tax", "BigDecimal", "8.10", 700012))
push_return(price_call, 0.000891, return_value=make_param("total", "BigDecimal", "98.07", 700013))

# Create order model
order_new_call = push_call({
    "defined_class": "Order",
    "method_id": "new",
    "path": "app/models/order.rb",
    "lineno": 5, "static": True,
    "receiver": make_receiver("Order", 800001, static=True),
    "parameters": [
        make_param("user_id", "Integer", "42", 800010),
        make_param("total", "BigDecimal", "98.07", 700013),
        make_param("status", "String", "pending", 800011)
    ]
})
push_return(order_new_call, 0.000123, return_value=make_param("order", "Order",
    '#<Order id: nil, user_id: 42, total: 98.07, status: "pending">', 800002))

order_valid = push_call({
    "defined_class": "Order",
    "method_id": "valid?",
    "path": "app/models/order.rb",
    "lineno": 34, "static": False,
    "receiver": make_receiver("Order", 800002),
    "parameters": []
})
push_return(order_valid, 0.001234, return_value=make_param("result", "TrueClass", "true", 2))

order_save = push_call({
    "defined_class": "ActiveRecord::Persistence",
    "method_id": "save!",
    "path": "gems/activerecord-7.0.4/lib/active_record/persistence.rb",
    "lineno": 143, "static": False,
    "receiver": make_receiver("Order", 800002),
    "parameters": []
})
order_insert_sql = push_call({
    "sql_query": {
        "database_type": "postgresql",
        "sql": 'INSERT INTO "orders" ("user_id", "total", "status", "created_at", "updated_at") VALUES ($1, $2, $3, $4, $5) RETURNING "id"',
        "server_version": "14.5"
    },
    "message": [make_param("binds", "Array", '["42", "98.07", "pending", "2024-01-15 11:00:00", "2024-01-15 11:00:00"]', 800020)]
})
push_return(order_insert_sql, 0.007891)

# Create line items
for i in range(1):  # just 1 line item for this product
    li_call = push_call({
        "defined_class": "LineItem",
        "method_id": "create!",
        "path": "app/models/line_item.rb",
        "lineno": 8, "static": True,
        "receiver": make_receiver("LineItem", 900001, static=True),
        "parameters": [
            make_param("order_id", "Integer", "nil", 900010),
            make_param("product_id", "Integer", "7", 100001),
            make_param("quantity", "Integer", "3", 100002),
            make_param("unit_price", "BigDecimal", "29.99", 900011)
        ]
    })
    li_sql = push_call({
        "sql_query": {
            "database_type": "postgresql",
            "sql": 'INSERT INTO "line_items" ("order_id", "product_id", "quantity", "unit_price") VALUES ($1, $2, $3, $4) RETURNING "id"',
            "server_version": "14.5"
        },
        "message": [make_param("binds", "Array", '["101", "7", "3", "29.99"]', 900020)]
    })
    push_return(li_sql, 0.003421)
    push_return(li_call, 0.004012, return_value=make_param("li", "LineItem",
        '#<LineItem id: 201, order_id: 101, product_id: 7, quantity: 3>', 900002))

push_return(order_save, 0.015234, return_value=make_param("order", "Order",
    '#<Order id: 101, user_id: 42, total: 98.07, status: "pending">', 800002))

# Update inventory
inv_update = push_call({
    "defined_class": "InventoryService",
    "method_id": "decrement_stock",
    "path": "app/services/inventory_service.rb",
    "lineno": 45, "static": False,
    "receiver": make_receiver("InventoryService", 500001),
    "parameters": [
        make_param("product_id", "Integer", "7", 100001),
        make_param("quantity", "Integer", "3", 100002)
    ]
})
inv_update_sql = push_call({
    "sql_query": {
        "database_type": "postgresql",
        "sql": 'UPDATE "products" SET "stock_count" = "stock_count" - $1, "updated_at" = $2 WHERE "products"."id" = $3',
        "server_version": "14.5"
    },
    "message": [make_param("binds", "Array", '["3", "2024-01-15 11:00:00", "7"]', 500020)]
})
push_return(inv_update_sql, 0.005123)
push_return(inv_update, 0.005891)

# Payment
pay_call = push_call({
    "defined_class": "PaymentService",
    "method_id": "charge",
    "path": "app/services/payment_service.rb",
    "lineno": 14, "static": False,
    "receiver": make_receiver("PaymentService", 1000001),
    "parameters": [
        make_param("user", "User", "#<User id: 42>", 200002),
        make_param("amount", "BigDecimal", "98.07", 700013),
        make_param("order_id", "Integer", "101", 800003)
    ]
})

# Stripe API call
stripe_call = push_call({
    "http_client_request": {
        "request_method": "POST",
        "url": "https://api.stripe.com/v1/payment_intents",
        "headers": {
            "authorization": "Bearer sk_test_xxx",
            "content-type": "application/x-www-form-urlencoded",
            "stripe-version": "2023-10-16"
        }
    },
    "message": [
        make_param("amount", "Integer", "9807", 1000010),
        make_param("currency", "String", "usd", 1000011),
        make_param("customer", "String", "cus_abc123", 1000012)
    ]
})
push_return(stripe_call, 0.342891, **{
    "http_client_response": {
        "status_code": 200,
        "headers": {"content-type": "application/json", "request-id": "req_stripe123"}
    }
})

# Record payment
payment_model = push_call({
    "defined_class": "Payment",
    "method_id": "create!",
    "path": "app/models/payment.rb",
    "lineno": 6, "static": True,
    "receiver": make_receiver("Payment", 1100001, static=True),
    "parameters": [
        make_param("order_id", "Integer", "101", 800003),
        make_param("amount", "BigDecimal", "98.07", 700013),
        make_param("stripe_payment_intent_id", "String", "pi_abc123", 1100010),
        make_param("status", "String", "succeeded", 1100011)
    ]
})
payment_sql = push_call({
    "sql_query": {
        "database_type": "postgresql",
        "sql": 'INSERT INTO "payments" ("order_id", "amount", "stripe_payment_intent_id", "status", "created_at") VALUES ($1, $2, $3, $4, $5) RETURNING "id"',
        "server_version": "14.5"
    },
    "message": [make_param("binds", "Array", '["101", "98.07", "pi_abc123", "succeeded", "2024-01-15 11:00:01"]', 1100020)]
})
push_return(payment_sql, 0.006234)
push_return(payment_model, 0.007012, return_value=make_param("payment", "Payment",
    '#<Payment id: 301, order_id: 101, amount: 98.07, status: "succeeded">', 1100002))
push_return(pay_call, 0.351234, return_value=make_param("payment", "Payment",
    '#<Payment id: 301, status: "succeeded">', 1100002))

# Update order status
order_update_call = push_call({
    "defined_class": "Order",
    "method_id": "update!",
    "path": "app/models/order.rb",
    "lineno": 52, "static": False,
    "receiver": make_receiver("Order", 800002),
    "parameters": [make_param("status", "String", "confirmed", 1200001)]
})
order_update_sql = push_call({
    "sql_query": {
        "database_type": "postgresql",
        "sql": 'UPDATE "orders" SET "status" = $1, "updated_at" = $2 WHERE "orders"."id" = $3',
        "server_version": "14.5"
    },
    "message": [make_param("binds", "Array", '["confirmed", "2024-01-15 11:00:01", "101"]', 1200010)]
})
push_return(order_update_sql, 0.004512)
push_return(order_update_call, 0.005123, return_value=make_param("order", "Order",
    '#<Order id: 101, status: "confirmed">', 800002))

# Notification
notif_call = push_call({
    "defined_class": "NotificationService",
    "method_id": "order_confirmed",
    "path": "app/services/notification_service.rb",
    "lineno": 18, "static": False,
    "receiver": make_receiver("NotificationService", 1300001),
    "parameters": [
        make_param("user", "User", "#<User id: 42>", 200002),
        make_param("order", "Order", '#<Order id: 101>', 800002)
    ]
})

# Email via SendGrid
email_call = push_call({
    "http_client_request": {
        "request_method": "POST",
        "url": "https://api.sendgrid.com/v3/mail/send",
        "headers": {
            "authorization": "Bearer SG.testkey",
            "content-type": "application/json"
        }
    },
    "message": [
        make_param("to", "String", "alice@example.com", 1300010),
        make_param("subject", "String", "Order #101 confirmed!", 1300011)
    ]
})
push_return(email_call, 0.187234, **{
    "http_client_response": {
        "status_code": 202,
        "headers": {"x-message-id": "msg_xyz789"}
    }
})
push_return(notif_call, 0.188012)

# Push notification
push_call_event = push_call({
    "defined_class": "NotificationService",
    "method_id": "send_push_notification",
    "path": "app/services/notification_service.rb",
    "lineno": 42, "static": False,
    "receiver": make_receiver("NotificationService", 1300001),
    "parameters": [
        make_param("user_id", "Integer", "42", 100010),
        make_param("message", "String", "Your order #101 has been confirmed!", 1400001)
    ]
})

# FCM call
fcm_call = push_call({
    "http_client_request": {
        "request_method": "POST",
        "url": "https://fcm.googleapis.com/fcm/send",
        "headers": {
            "authorization": "key=FCM_SERVER_KEY",
            "content-type": "application/json"
        }
    },
    "message": [make_param("to", "String", "/topics/user-42", 1400010)]
})
push_return(fcm_call, 0.098234, **{
    "http_client_response": {
        "status_code": 200,
        "headers": {"content-type": "application/json"}
    }
})
push_return(push_call_event, 0.099012)

push_return(svc_call, 0.680123, return_value=make_param("order", "Order",
    '#<Order id: 101, status: "confirmed", total: 98.07>', 800002))

push_return(orders_ctrl, 0.682341)

# HTTP response
push_return(http_call_id, 0.683892, **{
    "http_server_response": {
        "status_code": 201,
        "headers": {
            "content-type": "application/json; charset=utf-8",
            "location": "/orders/101",
            "x-request-id": "req-abc456",
            "cache-control": "no-cache"
        }
    }
})

appmap = {
    "version": "1.13.1",
    "metadata": {
        "name": "OrdersController#create processes a new order with payment and notifications",
        "app": "myapp",
        "language": {"name": "ruby", "engine": "ruby", "version": "3.2.0"},
        "frameworks": [
            {"name": "Ruby on Rails", "version": "7.0.4"},
            {"name": "RSpec", "version": "3.12.0"}
        ],
        "client": {"name": "appmap", "url": "https://github.com/getappmap/appmap-ruby", "version": "0.91.0"},
        "recorder": {"type": "tests", "name": "rspec"},
        "test_status": "succeeded",
        "source_location": "spec/controllers/orders_controller_spec.rb:18"
    },
    "classMap": [],
    "events": events
}

with open("large.appmap.json", "w") as f:
    json.dump(appmap, f, indent=2)

print(f"Generated large.appmap.json with {len(events)} events")
