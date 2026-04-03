#!/usr/bin/env python3
"""
Generate a realistic test suite of AppMap files simulating a Rails app.
Produces tmp/appmap/rspec/ with ~20 .appmap.json files covering:
  - Users CRUD (create, show, update, destroy, index)
  - Orders (create with payment, list, show, failure cases)
  - Auth (login success, login failure, logout)
  - Products (index, show)
  - Background mailer tests
"""
import json
import os
import re
import random
from copy import deepcopy

random.seed(0)

OUT_DIR = "tmp/appmap/rspec"
os.makedirs(OUT_DIR, exist_ok=True)

# ── Shared counter ────────────────────────────────────────────────────────────

class EventBuilder:
    def __init__(self):
        self.events = []
        self._eid = 1
        self._thread = 47219853920000

    def eid(self):
        v = self._eid; self._eid += 1; return v

    def call(self, **kw):
        e = {"id": self.eid(), "event": "call", "thread_id": self._thread}
        e.update(kw)
        self.events.append(e)
        return e["id"]

    def ret(self, parent_id, elapsed, **kw):
        e = {"id": self.eid(), "event": "return",
             "parent_id": parent_id, "elapsed": elapsed}
        e.update(kw)
        self.events.append(e)
        return e["id"]

    def fn_call(self, cls, meth, path, lineno, static=False, params=None, receiver_val=None):
        return self.call(
            defined_class=cls,
            method_id=meth,
            path=path,
            lineno=lineno,
            static=static,
            receiver={"name": "self", "class": cls,
                      "value": receiver_val or f"#<{cls}:0x{random.randint(0, 2**40):010x}>",
                      "object_id": random.randint(100000, 999999)},
            parameters=params or []
        )

    def fn_ret(self, parent_id, elapsed, ret_cls=None, ret_val=None, exc_cls=None, exc_msg=None):
        kw = {}
        if exc_cls:
            kw["exceptions"] = [{"class": exc_cls, "message": exc_msg,
                                  "object_id": random.randint(100000, 999999)}]
        elif ret_cls:
            kw["return_value"] = {"class": ret_cls, "value": ret_val or "",
                                   "object_id": random.randint(100000, 999999)}
        return self.ret(parent_id, elapsed, **kw)

    def sql(self, db_type, sql, binds=None, elapsed=None):
        cid = self.call(
            sql_query={"database_type": db_type, "sql": sql, "server_version": "14.5"},
            message=[{"name": "binds", "class": "Array",
                      "value": json.dumps(binds or []),
                      "object_id": random.randint(100000, 999999)}] if binds else []
        )
        self.ret(cid, elapsed or round(random.uniform(0.001, 0.012), 6))
        return cid

    def http_in(self, method, path, headers=None, message=None):
        hdrs = {
            "host": "localhost:3000",
            "content-type": "application/json",
            "accept": "application/json",
            "user-agent": "RSpec/3.12.0",
        }
        if headers:
            hdrs.update(headers)
        return self.call(
            http_server_request={"request_method": method, "path_info": path,
                                  "protocol": "HTTP/1.1", "headers": hdrs},
            message=message or []
        )

    def http_out(self, method, url, status, elapsed, headers_out=None, message=None):
        cid = self.call(
            http_client_request={"request_method": method, "url": url,
                                  "headers": headers_out or {"content-type": "application/json"}},
            message=message or []
        )
        self.ret(cid, elapsed, http_client_response={"status_code": status,
                                                       "headers": {"content-type": "application/json"}})
        return cid

    def http_out_ret(self, parent_id, status, elapsed):
        return self.ret(parent_id, elapsed,
                        http_server_response={"status_code": status,
                                              "headers": {"content-type": "application/json; charset=utf-8",
                                                          "cache-control": "no-cache"}})


# ── Helpers ───────────────────────────────────────────────────────────────────

def p(name, cls, val, oid=None):
    return {"name": name, "class": cls, "value": str(val),
            "object_id": oid or random.randint(100000, 999999)}

def make_appmap(name, test_status, events, source_location="spec/controllers/example_spec.rb:1",
                test_failure=None):
    meta = {
        "name": name,
        "app": "myapp",
        "language": {"name": "ruby", "engine": "ruby", "version": "3.2.0"},
        "frameworks": [
            {"name": "Ruby on Rails", "version": "7.0.4"},
            {"name": "RSpec", "version": "3.12.0"}
        ],
        "client": {"name": "appmap", "url": "https://github.com/getappmap/appmap-ruby",
                   "version": "0.91.0"},
        "recorder": {"type": "tests", "name": "rspec"},
        "git": {"repository": "https://github.com/myorg/myapp",
                "branch": "main", "commit": "a3f9c12", "status": []},
        "test_status": test_status,
        "source_location": source_location,
    }
    if test_failure:
        meta["test_failure"] = test_failure
    return {"version": "1.13.1", "metadata": meta, "classMap": [], "events": events}


def save(filename, appmap):
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w") as f:
        json.dump(appmap, f, indent=2)
    print(f"  {path} ({len(appmap['events'])} events)")


# ── Test Case Generators ──────────────────────────────────────────────────────

def make_users_index():
    b = EventBuilder()
    h = b.http_in("GET", "/users", message=[p("page", "Integer", 1), p("per_page", "Integer", 25)])
    c = b.fn_call("UsersController", "index", "app/controllers/users_controller.rb", 5)
    b.sql("postgresql", 'SELECT COUNT(*) FROM "users"', binds=[], elapsed=0.002)
    b.sql("postgresql", 'SELECT "users".* FROM "users" ORDER BY created_at DESC LIMIT $1 OFFSET $2',
          binds=[25, 0], elapsed=0.005)
    b.fn_ret(c, 0.011)
    b.http_out_ret(h, 200, 0.013)
    return make_appmap("UsersController index returns paginated users",
                       "succeeded", b.events, "spec/controllers/users_controller_spec.rb:10")

def make_users_show():
    b = EventBuilder()
    h = b.http_in("GET", "/users/42")
    c = b.fn_call("UsersController", "show", "app/controllers/users_controller.rb", 22)
    b.sql("postgresql", 'SELECT "users".* FROM "users" WHERE "users"."id" = $1 LIMIT $2',
          binds=[42, 1], elapsed=0.002)
    b.fn_ret(c, 0.005, "User", "#<User id: 42, email: 'alice@example.com'>")
    b.http_out_ret(h, 200, 0.007)
    return make_appmap("UsersController show returns user", "succeeded", b.events,
                       "spec/controllers/users_controller_spec.rb:25")

def make_users_show_not_found():
    b = EventBuilder()
    h = b.http_in("GET", "/users/9999")
    c = b.fn_call("UsersController", "show", "app/controllers/users_controller.rb", 22)
    b.sql("postgresql", 'SELECT "users".* FROM "users" WHERE "users"."id" = $1 LIMIT $2',
          binds=[9999, 1], elapsed=0.002)
    # ActiveRecord::RecordNotFound
    b.fn_ret(c, 0.004, exc_cls="ActiveRecord::RecordNotFound",
             exc_msg="Couldn't find User with 'id'=9999")
    b.http_out_ret(h, 404, 0.005)
    return make_appmap("UsersController show returns 404 for unknown user",
                       "succeeded", b.events, "spec/controllers/users_controller_spec.rb:35")

def make_users_create_success():
    b = EventBuilder()
    h = b.http_in("POST", "/users", message=[
        p("email", "String", "bob@example.com"),
        p("name", "String", "Bob Jones"),
        p("password", "String", "[FILTERED]")
    ])
    c = b.fn_call("UsersController", "create", "app/controllers/users_controller.rb", 40)
    up = b.fn_call("UsersController", "user_params", "app/controllers/users_controller.rb", 75,
                   params=[])
    b.fn_ret(up, 0.0002, "ActionController::Parameters",
             '{"email"=>"bob@example.com","name"=>"Bob Jones"}')
    svc = b.fn_call("UserRegistrationService", "call",
                    "app/services/user_registration_service.rb", 8, params=[
                        p("params", "ActionController::Parameters", '{"email"=>"bob@example.com"}')
                    ])
    # email uniqueness check
    rel = b.fn_call("ActiveRecord::Relation", "exists?",
                    "gems/activerecord-7.0.4/lib/active_record/relation.rb", 356, params=[
                        p("conditions", "Hash", '{"email"=>"bob@example.com"}')
                    ])
    b.sql("postgresql",
          'SELECT 1 AS one FROM "users" WHERE "users"."email" = $1 LIMIT $2',
          binds=["bob@example.com", 1], elapsed=0.003)
    b.fn_ret(rel, 0.004, "FalseClass", "false")
    # create
    cu = b.fn_call("UserRegistrationService", "create_user",
                   "app/services/user_registration_service.rb", 42, params=[
                       p("email", "String", "bob@example.com"),
                       p("name", "String", "Bob Jones"),
                       p("password_digest", "String", "$2a$12$...")
                   ])
    b.sql("postgresql",
          'INSERT INTO "users" ("email","name","password_digest","created_at","updated_at") VALUES ($1,$2,$3,$4,$5) RETURNING "id"',
          binds=["bob@example.com", "Bob Jones", "$2a$12$...", "2024-01-15 10:00:00"], elapsed=0.008)
    b.fn_ret(cu, 0.012, "User", '#<User id: 99, email: "bob@example.com">')
    # email
    em = b.fn_call("UserRegistrationService", "send_welcome_email",
                   "app/services/user_registration_service.rb", 58, params=[
                       p("user", "User", '#<User id: 99, email: "bob@example.com">')
                   ])
    b.http_out("POST", "https://api.sendgrid.com/v3/mail/send", 202, 0.187,
               message=[p("to", "String", "bob@example.com"),
                        p("subject", "String", "Welcome to MyApp!")])
    b.fn_ret(em, 0.189)
    b.fn_ret(svc, 0.209, "User", '#<User id: 99, email: "bob@example.com">')
    b.fn_ret(c, 0.211)
    b.http_out_ret(h, 201, 0.213)
    return make_appmap("UsersController create registers a new user", "succeeded", b.events,
                       "spec/controllers/users_controller_spec.rb:48")

def make_users_create_duplicate_email():
    b = EventBuilder()
    h = b.http_in("POST", "/users", message=[
        p("email", "String", "alice@example.com"),  # already exists
        p("name", "String", "Alice Dupe"),
        p("password", "String", "[FILTERED]")
    ])
    c = b.fn_call("UsersController", "create", "app/controllers/users_controller.rb", 40)
    up = b.fn_call("UsersController", "user_params", "app/controllers/users_controller.rb", 75)
    b.fn_ret(up, 0.0002, "ActionController::Parameters", '{"email"=>"alice@example.com"}')
    svc = b.fn_call("UserRegistrationService", "call",
                    "app/services/user_registration_service.rb", 8, params=[
                        p("params", "ActionController::Parameters", '{"email"=>"alice@example.com"}')
                    ])
    rel = b.fn_call("ActiveRecord::Relation", "exists?",
                    "gems/activerecord-7.0.4/lib/active_record/relation.rb", 356, params=[
                        p("conditions", "Hash", '{"email"=>"alice@example.com"}')
                    ])
    b.sql("postgresql",
          'SELECT 1 AS one FROM "users" WHERE "users"."email" = $1 LIMIT $2',
          binds=["alice@example.com", 1], elapsed=0.003)
    b.fn_ret(rel, 0.004, "TrueClass", "true")   # email exists!
    b.fn_ret(svc, 0.005, exc_cls="UserRegistrationService::DuplicateEmailError",
             exc_msg="Email alice@example.com is already registered")
    b.fn_ret(c, 0.006)
    b.http_out_ret(h, 422, 0.007)
    return make_appmap("UsersController create returns 422 for duplicate email",
                       "succeeded", b.events, "spec/controllers/users_controller_spec.rb:65")

def make_users_update():
    b = EventBuilder()
    h = b.http_in("PATCH", "/users/42", message=[p("name", "String", "Alice Updated")])
    c = b.fn_call("UsersController", "update", "app/controllers/users_controller.rb", 55)
    b.sql("postgresql", 'SELECT "users".* FROM "users" WHERE "users"."id" = $1 LIMIT $2',
          binds=[42, 1], elapsed=0.002)
    b.sql("postgresql", 'UPDATE "users" SET "name" = $1, "updated_at" = $2 WHERE "users"."id" = $3',
          binds=["Alice Updated", "2024-01-15 11:00:00", 42], elapsed=0.006)
    b.fn_ret(c, 0.011, "User", '#<User id: 42, name: "Alice Updated">')
    b.http_out_ret(h, 200, 0.013)
    return make_appmap("UsersController update updates user attributes", "succeeded",
                       b.events, "spec/controllers/users_controller_spec.rb:80")

def make_users_destroy():
    b = EventBuilder()
    h = b.http_in("DELETE", "/users/42")
    c = b.fn_call("UsersController", "destroy", "app/controllers/users_controller.rb", 68)
    b.sql("postgresql", 'SELECT "users".* FROM "users" WHERE "users"."id" = $1 LIMIT $2',
          binds=[42, 1], elapsed=0.002)
    b.sql("postgresql", 'DELETE FROM "users" WHERE "users"."id" = $1', binds=[42], elapsed=0.004)
    b.fn_ret(c, 0.009)
    b.http_out_ret(h, 204, 0.010)
    return make_appmap("UsersController destroy deletes a user", "succeeded", b.events,
                       "spec/controllers/users_controller_spec.rb:91")

def make_auth_login_success():
    b = EventBuilder()
    h = b.http_in("POST", "/sessions", message=[
        p("email", "String", "alice@example.com"),
        p("password", "String", "[FILTERED]")
    ])
    c = b.fn_call("SessionsController", "create", "app/controllers/sessions_controller.rb", 8)
    b.sql("postgresql", 'SELECT "users".* FROM "users" WHERE "users"."email" = $1 LIMIT $2',
          binds=["alice@example.com", 1], elapsed=0.003)
    pw = b.fn_call("BCrypt::Password", "is_password?",
                   "gems/bcrypt-3.1.18/lib/bcrypt/password.rb", 62, params=[
                       p("secret", "String", "[FILTERED]")
                   ])
    b.fn_ret(pw, 0.078, "TrueClass", "true")  # slow bcrypt
    jwt = b.fn_call("JwtService", "encode", "app/services/jwt_service.rb", 12, params=[
        p("payload", "Hash", '{"user_id"=>42,"exp":1705322400}')
    ])
    b.fn_ret(jwt, 0.0003, "String", "eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjo0Mn0.test")
    b.fn_ret(c, 0.083, "String", "eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjo0Mn0.test")
    b.http_out_ret(h, 201, 0.084)
    return make_appmap("SessionsController create authenticates with valid credentials",
                       "succeeded", b.events, "spec/controllers/sessions_controller_spec.rb:12")

def make_auth_login_failure():
    b = EventBuilder()
    h = b.http_in("POST", "/sessions", message=[
        p("email", "String", "alice@example.com"),
        p("password", "String", "[FILTERED]")
    ])
    c = b.fn_call("SessionsController", "create", "app/controllers/sessions_controller.rb", 8)
    b.sql("postgresql", 'SELECT "users".* FROM "users" WHERE "users"."email" = $1 LIMIT $2',
          binds=["alice@example.com", 1], elapsed=0.003)
    pw = b.fn_call("BCrypt::Password", "is_password?",
                   "gems/bcrypt-3.1.18/lib/bcrypt/password.rb", 62, params=[
                       p("secret", "String", "[FILTERED]")
                   ])
    b.fn_ret(pw, 0.081, "FalseClass", "false")  # wrong password
    b.fn_ret(c, 0.086)
    b.http_out_ret(h, 401, 0.087)
    return make_appmap("SessionsController create rejects invalid password",
                       "succeeded", b.events, "spec/controllers/sessions_controller_spec.rb:28")

def make_orders_create_success():
    b = EventBuilder()
    h = b.http_in("POST", "/orders", headers={"authorization": "Bearer tok.abc"},
                  message=[p("product_id", "Integer", 7), p("quantity", "Integer", 2)])
    auth = b.fn_call("AuthenticationConcern", "authenticate_user!",
                     "app/controllers/concerns/authentication_concern.rb", 5)
    b.sql("postgresql", 'SELECT "users".* FROM "users" WHERE "users"."id" = $1 LIMIT $2',
          binds=[42, 1], elapsed=0.002)
    b.fn_ret(auth, 0.003, "User", "#<User id: 42>")
    c = b.fn_call("OrdersController", "create", "app/controllers/orders_controller.rb", 15)
    b.sql("postgresql", 'SELECT "products".* FROM "products" WHERE "products"."id" = $1 LIMIT $2',
          binds=[7, 1], elapsed=0.002)
    b.sql("postgresql", 'SELECT "products"."stock_count" FROM "products" WHERE "products"."id" = $1 FOR UPDATE',
          binds=[7], elapsed=0.004)
    b.sql("postgresql", 'INSERT INTO "orders" ("user_id","total","status","created_at","updated_at") VALUES ($1,$2,$3,$4,$5) RETURNING "id"',
          binds=[42, "59.98", "pending", "2024-01-15 10:00:00", "2024-01-15 10:00:00"], elapsed=0.008)
    b.sql("postgresql", 'INSERT INTO "line_items" ("order_id","product_id","quantity","unit_price") VALUES ($1,$2,$3,$4) RETURNING "id"',
          binds=[101, 7, 2, "29.99"], elapsed=0.004)
    b.sql("postgresql", 'UPDATE "products" SET "stock_count" = "stock_count" - $1 WHERE "products"."id" = $2',
          binds=[2, 7], elapsed=0.005)
    b.http_out("POST", "https://api.stripe.com/v1/payment_intents", 200, 0.312,
               message=[p("amount", "Integer", 5998), p("currency", "String", "usd")])
    b.sql("postgresql", 'INSERT INTO "payments" ("order_id","amount","stripe_payment_intent_id","status") VALUES ($1,$2,$3,$4) RETURNING "id"',
          binds=[101, "59.98", "pi_abc123", "succeeded"], elapsed=0.006)
    b.sql("postgresql", 'UPDATE "orders" SET "status" = $1 WHERE "orders"."id" = $2',
          binds=["confirmed", 101], elapsed=0.004)
    b.http_out("POST", "https://api.sendgrid.com/v3/mail/send", 202, 0.143,
               message=[p("to", "String", "alice@example.com"),
                        p("subject", "String", "Order #101 confirmed!")])
    b.fn_ret(c, 0.502)
    b.http_out_ret(h, 201, 0.504)
    return make_appmap("OrdersController create places an order and charges payment",
                       "succeeded", b.events, "spec/controllers/orders_controller_spec.rb:18")

def make_orders_create_payment_failure():
    b = EventBuilder()
    h = b.http_in("POST", "/orders", headers={"authorization": "Bearer tok.abc"},
                  message=[p("product_id", "Integer", 7), p("quantity", "Integer", 100)])  # too many
    auth = b.fn_call("AuthenticationConcern", "authenticate_user!",
                     "app/controllers/concerns/authentication_concern.rb", 5)
    b.sql("postgresql", 'SELECT "users".* FROM "users" WHERE "users"."id" = $1 LIMIT $2',
          binds=[42, 1], elapsed=0.002)
    b.fn_ret(auth, 0.003, "User", "#<User id: 42>")
    c = b.fn_call("OrdersController", "create", "app/controllers/orders_controller.rb", 15)
    b.sql("postgresql", 'SELECT "products".* FROM "products" WHERE "products"."id" = $1 LIMIT $2',
          binds=[7, 1], elapsed=0.002)
    b.sql("postgresql", 'SELECT "products"."stock_count" FROM "products" WHERE "products"."id" = $1 FOR UPDATE',
          binds=[7], elapsed=0.004)
    b.fn_ret(c, 0.008, exc_cls="InsufficientStockError",
             exc_msg="Only 50 units of product 7 available, requested 100")
    b.http_out_ret(h, 422, 0.009)
    return make_appmap("OrdersController create returns 422 when stock is insufficient",
                       "succeeded", b.events, "spec/controllers/orders_controller_spec.rb:45")

def make_orders_create_stripe_failure():
    """Test where Stripe API returns an error — this test itself FAILS."""
    b = EventBuilder()
    h = b.http_in("POST", "/orders", headers={"authorization": "Bearer tok.abc"},
                  message=[p("product_id", "Integer", 7), p("quantity", "Integer", 2)])
    auth = b.fn_call("AuthenticationConcern", "authenticate_user!",
                     "app/controllers/concerns/authentication_concern.rb", 5)
    b.sql("postgresql", 'SELECT "users".* FROM "users" WHERE "users"."id" = $1 LIMIT $2',
          binds=[42, 1], elapsed=0.002)
    b.fn_ret(auth, 0.003, "User", "#<User id: 42>")
    c = b.fn_call("OrdersController", "create", "app/controllers/orders_controller.rb", 15)
    b.sql("postgresql", 'SELECT "products".* FROM "products" WHERE "products"."id" = $1 LIMIT $2',
          binds=[7, 1], elapsed=0.002)
    b.sql("postgresql", 'SELECT "products"."stock_count" FROM "products" WHERE "products"."id" = $1 FOR UPDATE',
          binds=[7], elapsed=0.004)
    b.sql("postgresql", 'INSERT INTO "orders" ("user_id","total","status","created_at","updated_at") VALUES ($1,$2,$3,$4,$5) RETURNING "id"',
          binds=[42, "59.98", "pending"], elapsed=0.008)
    b.sql("postgresql", 'INSERT INTO "line_items" ("order_id","product_id","quantity","unit_price") VALUES ($1,$2,$3,$4) RETURNING "id"',
          binds=[101, 7, 2, "29.99"], elapsed=0.004)
    b.http_out("POST", "https://api.stripe.com/v1/payment_intents", 402, 0.287,
               message=[p("amount", "Integer", 5998)])  # card declined!
    # Expected 201 but got 402 because rollback wasn't happening — test fails
    b.fn_ret(c, 0.291, exc_cls="Stripe::CardError", exc_msg="Your card was declined.")
    b.http_out_ret(h, 500, 0.292)
    return make_appmap(
        "OrdersController create rolls back transaction when Stripe fails",
        "failed", b.events, "spec/controllers/orders_controller_spec.rb:72",
        test_failure={
            "message": "expected HTTP status 422 but got 500",
            "location": "spec/controllers/orders_controller_spec.rb:89"
        }
    )

def make_orders_index():
    b = EventBuilder()
    h = b.http_in("GET", "/orders", headers={"authorization": "Bearer tok.abc"},
                  message=[p("status", "String", "confirmed")])
    auth = b.fn_call("AuthenticationConcern", "authenticate_user!",
                     "app/controllers/concerns/authentication_concern.rb", 5)
    b.sql("postgresql", 'SELECT "users".* FROM "users" WHERE "users"."id" = $1 LIMIT $2',
          binds=[42, 1], elapsed=0.002)
    b.fn_ret(auth, 0.003, "User", "#<User id: 42>")
    c = b.fn_call("OrdersController", "index", "app/controllers/orders_controller.rb", 5)
    b.sql("postgresql",
          'SELECT "orders".* FROM "orders" WHERE "orders"."user_id" = $1 AND "orders"."status" = $2 ORDER BY created_at DESC',
          binds=[42, "confirmed"], elapsed=0.006)
    b.fn_ret(c, 0.012)
    b.http_out_ret(h, 200, 0.014)
    return make_appmap("OrdersController index lists user orders filtered by status",
                       "succeeded", b.events, "spec/controllers/orders_controller_spec.rb:98")

def make_products_index():
    b = EventBuilder()
    h = b.http_in("GET", "/products", message=[p("category", "String", "electronics")])
    c = b.fn_call("ProductsController", "index", "app/controllers/products_controller.rb", 5)
    b.sql("postgresql", 'SELECT COUNT(*) FROM "products" WHERE "products"."category" = $1',
          binds=["electronics"], elapsed=0.002)
    b.sql("postgresql",
          'SELECT "products".* FROM "products" WHERE "products"."category" = $1 ORDER BY name ASC LIMIT $2',
          binds=["electronics", 50], elapsed=0.007)
    b.fn_ret(c, 0.013)
    b.http_out_ret(h, 200, 0.015)
    return make_appmap("ProductsController index lists products by category", "succeeded",
                       b.events, "spec/controllers/products_controller_spec.rb:8")

def make_products_show():
    b = EventBuilder()
    h = b.http_in("GET", "/products/7")
    c = b.fn_call("ProductsController", "show", "app/controllers/products_controller.rb", 22)
    b.sql("postgresql", 'SELECT "products".* FROM "products" WHERE "products"."id" = $1 LIMIT $2',
          binds=[7, 1], elapsed=0.002)
    # also fetch related
    b.sql("postgresql",
          'SELECT "reviews".* FROM "reviews" WHERE "reviews"."product_id" = $1 ORDER BY created_at DESC LIMIT $2',
          binds=[7, 5], elapsed=0.004)
    b.fn_ret(c, 0.009)
    b.http_out_ret(h, 200, 0.010)
    return make_appmap("ProductsController show returns product with reviews", "succeeded",
                       b.events, "spec/controllers/products_controller_spec.rb:22")

def make_user_mailer_welcome():
    b = EventBuilder()
    c = b.fn_call("UserMailer", "welcome_email", "app/mailers/user_mailer.rb", 6,
                  params=[p("user", "User", "#<User id: 99>")])
    tmpl = b.fn_call("ActionMailer::MessageDelivery", "deliver_now",
                     "gems/actionmailer-7.0.4/lib/action_mailer/message_delivery.rb", 120)
    b.http_out("POST", "https://api.sendgrid.com/v3/mail/send", 202, 0.192,
               message=[p("to", "String", "bob@example.com"),
                        p("subject", "String", "Welcome to MyApp!")])
    b.fn_ret(tmpl, 0.195)
    b.fn_ret(c, 0.196)
    return make_appmap("UserMailer welcome_email sends welcome email via SendGrid", "succeeded",
                       b.events, "spec/mailers/user_mailer_spec.rb:8")

def make_user_mailer_failure():
    """Test that fails because SendGrid returns 500."""
    b = EventBuilder()
    c = b.fn_call("UserMailer", "welcome_email", "app/mailers/user_mailer.rb", 6,
                  params=[p("user", "User", "#<User id: 99>")])
    tmpl = b.fn_call("ActionMailer::MessageDelivery", "deliver_now",
                     "gems/actionmailer-7.0.4/lib/action_mailer/message_delivery.rb", 120)
    b.http_out("POST", "https://api.sendgrid.com/v3/mail/send", 500, 0.241,
               message=[p("to", "String", "bob@example.com")])
    b.fn_ret(tmpl, 0.244, exc_cls="SendGrid::Error", exc_msg="Internal server error from SendGrid")
    b.fn_ret(c, 0.245, exc_cls="SendGrid::Error", exc_msg="Internal server error from SendGrid")
    return make_appmap(
        "UserMailer welcome_email retries on transient SendGrid errors",
        "failed", b.events, "spec/mailers/user_mailer_spec.rb:22",
        test_failure={
            "message": "expected no exception but SendGrid::Error was raised",
            "location": "spec/mailers/user_mailer_spec.rb:31"
        }
    )

def make_search_users():
    b = EventBuilder()
    h = b.http_in("GET", "/users/search",
                  message=[p("q", "String", "alice"), p("role", "String", "admin")])
    c = b.fn_call("UsersController", "search", "app/controllers/users_controller.rb", 82)
    # Full-text search
    b.sql("postgresql",
          "SELECT \"users\".* FROM \"users\" WHERE (\"users\".\"name\" ILIKE $1 OR \"users\".\"email\" ILIKE $2) AND \"users\".\"role\" = $3 ORDER BY name ASC LIMIT $4",
          binds=["%alice%", "%alice%", "admin", 20], elapsed=0.023)
    b.fn_ret(c, 0.028)
    b.http_out_ret(h, 200, 0.030)
    return make_appmap("UsersController search finds users by name/email with role filter",
                       "succeeded", b.events, "spec/controllers/users_controller_spec.rb:105")

def make_rate_limit_exceeded():
    """Test that exercises rate limiting logic."""
    b = EventBuilder()
    h = b.http_in("POST", "/sessions", message=[p("email", "String", "alice@example.com"),
                                                 p("password", "String", "[FILTERED]")])
    c = b.fn_call("SessionsController", "create", "app/controllers/sessions_controller.rb", 8)
    rl = b.fn_call("RateLimitConcern", "check_rate_limit!",
                   "app/controllers/concerns/rate_limit_concern.rb", 12, params=[
                       p("key", "String", "login:alice@example.com")
                   ])
    # Redis check (via SQL-like interface for caching)
    b.sql("postgresql",
          'SELECT "rate_limit_counters"."count" FROM "rate_limit_counters" WHERE "rate_limit_counters"."key" = $1',
          binds=["login:alice@example.com"], elapsed=0.001)
    b.fn_ret(rl, 0.002, exc_cls="RateLimitExceeded",
             exc_msg="Too many login attempts. Try again in 300 seconds.")
    b.fn_ret(c, 0.003)
    b.http_out_ret(h, 429, 0.004)
    return make_appmap("SessionsController create enforces rate limiting after too many attempts",
                       "succeeded", b.events, "spec/controllers/sessions_controller_spec.rb:45")


# ── Main ─────────────────────────────────────────────────────────────────────

TESTS = [
    ("UsersController_index_returns_paginated_users.appmap.json", make_users_index),
    ("UsersController_show_returns_user.appmap.json", make_users_show),
    ("UsersController_show_returns_404_for_unknown_user.appmap.json", make_users_show_not_found),
    ("UsersController_create_registers_a_new_user.appmap.json", make_users_create_success),
    ("UsersController_create_returns_422_for_duplicate_email.appmap.json", make_users_create_duplicate_email),
    ("UsersController_update_updates_user_attributes.appmap.json", make_users_update),
    ("UsersController_destroy_deletes_a_user.appmap.json", make_users_destroy),
    ("UsersController_search_finds_users.appmap.json", make_search_users),
    ("SessionsController_create_authenticates_with_valid_credentials.appmap.json", make_auth_login_success),
    ("SessionsController_create_rejects_invalid_password.appmap.json", make_auth_login_failure),
    ("SessionsController_create_enforces_rate_limiting.appmap.json", make_rate_limit_exceeded),
    ("OrdersController_create_places_an_order.appmap.json", make_orders_create_success),
    ("OrdersController_create_returns_422_insufficient_stock.appmap.json", make_orders_create_payment_failure),
    ("OrdersController_create_rolls_back_when_stripe_fails.appmap.json", make_orders_create_stripe_failure),
    ("OrdersController_index_lists_user_orders.appmap.json", make_orders_index),
    ("ProductsController_index_lists_products.appmap.json", make_products_index),
    ("ProductsController_show_returns_product_with_reviews.appmap.json", make_products_show),
    ("UserMailer_welcome_email_sends_email.appmap.json", make_user_mailer_welcome),
    ("UserMailer_welcome_email_retries_on_errors.appmap.json", make_user_mailer_failure),
]

print(f"Generating {len(TESTS)} appmap files in {OUT_DIR}/")
total_events = 0
for filename, fn in TESTS:
    am = fn()
    save(filename, am)
    total_events += len(am["events"])

total_size = sum(
    os.path.getsize(os.path.join(OUT_DIR, f))
    for f, _ in TESTS
)
print(f"\nTotal: {len(TESTS)} files, {total_events} events, {total_size/1024:.0f} KB")
