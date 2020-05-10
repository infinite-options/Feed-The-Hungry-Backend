#To run program:  python3 fth_api.py prashant

#README:  if conn error make sure password is set properly in RDS PASSWORD section

#README:  Debug Mode may need to be set to Fales when deploying live (although it seems to be working through Zappa)

#README:  if there are errors, make sure you have all requirements are loaded
#pip3 install flask
#pip3 install flask_restful
#pip3 install flask_cors
#pip3 install Werkzeug
#pip3 install pymysql
#pip3 install python-dateutil


from flask import Flask, request, render_template
from flask_restful import Resource, Api
from flask_cors import CORS

from werkzeug.exceptions import BadRequest, NotFound

from dateutil.relativedelta import *
from decimal import Decimal
from datetime import datetime, date, timedelta
from hashlib import sha512
from math import ceil

import decimal
import sys
import json
import pymysql

RDS_HOST = 'pm-mysqldb.cxjnrciilyjq.us-west-1.rds.amazonaws.com'
#RDS_HOST = 'localhost'
RDS_PORT = 3306
#RDS_USER = 'root'
RDS_USER = 'admin'
RDS_DB = 'feed_the_hungry'

app = Flask(__name__)

# Allow cross-origin resource sharing
cors = CORS(app, resources={r'/api/*': {'origins': '*'}})

# Set this to false when deploying to live application
app.config['DEBUG'] = True

# API
api = Api(app)

# Get RDS password from command line argument
def RdsPw():
    if len(sys.argv) == 2:
        return str(sys.argv[1])
    return ""

# RDS PASSWORD
# When deploying to Zappa, set RDS_PW equal to the password as a string
# When pushing to GitHub, set RDS_PW equal to RdsPw()
RDS_PW = 'prashant'
# RDS_PW = RdsPw()


getToday = lambda: datetime.strftime(date.today(), "%Y-%m-%d")
getNow = lambda: datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S")

# Connect to RDS
def getRdsConn(RDS_PW):
    global RDS_HOST
    global RDS_PORT
    global RDS_USER
    global RDS_DB

    print("Trying to connect to RDS...")
    try:
        conn = pymysql.connect(RDS_HOST,
                               user=RDS_USER,
                               port=RDS_PORT,
                               passwd=RDS_PW,
                               db=RDS_DB)
        cur = conn.cursor()
        print("Successfully connected to RDS.")
        return [conn, cur]
    except:
        print("Could not connect to RDS.")
        raise Exception("RDS Connection failed.")

# Connect to MySQL database (API v2)
def connect():
    global RDS_PW
    global RDS_HOST
    global RDS_PORT
    global RDS_USER
    global RDS_DB

    print("Trying to connect to RDS (API v2)...")
    try:
        conn = pymysql.connect( RDS_HOST,
                                user=RDS_USER,
                                port=RDS_PORT,
                                passwd=RDS_PW,
                                db=RDS_DB,
                                cursorclass=pymysql.cursors.DictCursor)
        print("Successfully connected to RDS. (API v2)")
        return conn
    except:
        print("Could not connect to RDS. (API v2)")
        raise Exception("RDS Connection failed. (API v2)")

# Disconnect from MySQL database (API v2)
def disconnect(conn):
    try:
        conn.close()
        print("Successfully disconnected from MySQL database. (API v2)")
    except:
        print("Could not properly disconnect from MySQL database. (API v2)")
        raise Exception("Failure disconnecting from MySQL database. (API v2)")

# Serialize JSON
def serializeResponse(response):
    try:
        for row in response:
            for key in row:
                if type(row[key]) is Decimal:
                    row[key] = float(row[key])
                elif type(row[key]) is date or type(row[key]) is datetime:
                    row[key] = row[key].strftime("%Y-%m-%d")
        return response
    except:
        raise Exception("Bad query JSON")

# Execute an SQL command (API v2)
# Set cmd parameter to 'get' or 'post'
# Set conn parameter to connection object
# OPTIONAL: Set skipSerialization to True to skip default JSON response serialization
def execute(sql, cmd, conn, skipSerialization = False):
    response = {}
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            if cmd is 'get':
                result = cur.fetchall()
                response['message'] = 'Successfully executed SQL query.'
                # Return status code of 280 for successful GET request
                response['code'] = 280
                if not skipSerialization:
                    result = serializeResponse(result)
                response['result'] = result
            elif cmd in 'post':
                conn.commit()
                response['message'] = 'Successfully committed SQL command.'
                # Return status code of 281 for successful POST request
                response['code'] = 281
            else:
                response['message'] = 'Request failed. Unknown or ambiguous instruction given for MySQL command.'
                # Return status code of 480 for unknown HTTP method
                response['code'] = 480
    except:
        response['message'] = 'Request failed, could not execute MySQL command.'
        # Return status code of 490 for unsuccessful HTTP request
        response['code'] = 490
    finally:
        response['sql'] = sql
        return response

# Close RDS connection
def closeRdsConn(cur, conn):
    try:
        cur.close()
        conn.close()
        print("Successfully closed RDS connection.")
    except:
        print("Could not close RDS connection.")

# Runs a select query with the SQL query string and pymysql cursor as arguments
# Returns a list of Python tuples
def runSelectQuery(query, cur):
    try:
        cur.execute(query)
        queriedData = cur.fetchall()
        return queriedData
    except:
        raise Exception("Could not run select query and/or return data")


# -- Queries start here -------------------------------------------------------------------------------

# DONOR QUERIES - ROHAN

# QUERY 1
# DONATION INFORMATION: FoodBankID, FoodbankName, Donor Name, Total Donations
class DonorValuation(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
                SELECT temp.foodbank_id
                    , fb.foodbank_name
                    , donor_id
                    , d.first_name
                    , d.last_name
                    , sum(total) totalDonation
                FROM (
                    SELECT foodbank_id, donor_id, foodID, round(count(foodID) * value, 2) total
                    FROM (
                        SELECT foodbank_id
                            , donor_id
                            , trim('"' FROM cast(json_extract(donations.food_id, val) as CHAR)) AS foodID
                        FROM donations
                        JOIN numbers ON JSON_LENGTH(food_id) > n - 1)
                            AS t
                    JOIN food_list fl ON fl.food_id = t.foodID
                    GROUP BY foodbank_id, donor_id, foodID)
                        AS temp
                LEFT JOIN donor d ON d.DonorID = temp.donor_id
                JOIN foodbanks fb ON temp.foodbank_id = fb.foodbank_id
                GROUP BY foodbank_id, donor_id;""", 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# QUERY 2
# DONATED ITEMS BY FOODBANK
class ItemDonations(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
                SELECT t.foodbank_id
                    , foodbank_name
                    , foodID, item
                    , TotalDonation
                FROM (
                    SELECT foodbank_id, foodID, count(foodID) TotalDonation
                    FROM (
                        SELECT foodbank_id
                            , trim('"' FROM cast(json_extract(donations.food_id, val) AS CHAR)) AS foodID
                        FROM donations
                        JOIN numbers ON JSON_LENGTH(food_id) > n - 1)
                        AS temp
                GROUP BY foodbank_id, foodID) t
                JOIN food_list fl ON fl.food_id = t.foodID
                JOIN foodbanks fb ON t.foodbank_id = fb.foodbank_id
                ORDER BY TotalDonation DESC;""", 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)


# QUERY 3
# TYPES OF FOOD DONATED
class TypesOfFood(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
                SELECT temp.foodbank_id
                    , foodbank_name
                    , type
                    , count(type) typetotal
                FROM (
                    SELECT foodbank_id
                        , trim('"' FROM cast(json_extract(donations.food_id, val) AS CHAR)) AS foodID
                    FROM donations
                    JOIN numbers on JSON_LENGTH(food_id) > n - 1)
                    AS temp
                JOIN food_list fl ON temp.foodID = fl.food_id
                JOIN foodbanks fb ON fb.foodbank_id = temp.foodbank_id
                GROUP BY foodbank_id, type;""", 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# QUERY 4
# DONATIONS BY DATE
class DonationbyDate(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
                SELECT temp.foodbank_id
                    , fb.foodbank_name
                    , dateselected
                    , foodID
                    , item
                FROM (
                    SELECT foodbank_id
                        , date(STR_TO_DATE(date, '%c-%e-%Y %H:%i:%s')) AS dateselected
                        , trim('"' FROM cast(json_extract(donations.food_id, val) as CHAR)) AS foodID
                    FROM donations
                    JOIN numbers ON JSON_LENGTH(food_id) > n - 1)
                    AS temp
                JOIN food_list fl ON temp.foodID = fl.food_id
                JOIN foodbanks fb ON fb.foodbank_id = temp.foodbank_id
                GROUP BY foodbank_id, dateselected, foodID, item;""", 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

            
# ORDER STATUS QUERIES - PRAGYA

# Shows FoodBankID, Month, Completed Orders, Pending Orders, Total Orders
class OrderStatus(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute(""" Select foodbank_id, Month, CompletedOrders, PendingOrders,TotalOrders from
                (Select foodbank_id,
                month,
                sum(case when status = 'completed' then 1 else 0 end)
                AS CompletedOrders,
                count(*) - sum(case when status = 'completed' then 1 else 0 end) as PendingOrders,
                count(*) as TotalOrders
                from
                (SELECT foodbank_id, (Month(STR_TO_DATE(timestamp, '%c-%e-%Y %H:%i:%s'))) as Month, status from orders
                ) as s
                group by month, foodbank_id
                order by foodbank_id)
                as temp;""", 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)


# INVENTORY QUERIES - ISSEI

# QUERY : EXCESS INVENTORY
class ExcessInventory(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
            SELECT tmp.foodbank_id, foodbank_name, food_id,item, averageOrder, qty, excess
            FROM (
                SELECT foodbank_id, item, excessList.food_id, averageOrder, qty, excess
                FROM (
                    SELECT inventory.foodbank_id, food_id, averageOrder, qty, (qty - averageOrder) as excess from (
                        SELECT foodbank_id, foodID, (count(foodID)/3) as averageOrder from(
                            SELECT foodbank_id, trim('"' from cast(json_extract(list, val) as CHAR)) as foodID
                            from orders
                            join numbers on JSON_LENGTH(list) >= n
                            where DATE(STR_TO_DATE(timestamp, '%c-%e-%Y %H:%i:%s')) < '2021-07-04') temp
                        group by foodID, foodbank_id) ordercount
                    inner join inventory on foodID = food_id and ordercount.foodbank_id = inventory.foodbank_id
                    where qty > averageOrder)
                AS excessList
                LEFT JOIN food_list ON food_list.food_id = excessList.food_id)
            AS tmp
            LEFT JOIN foodbanks ON foodbanks.foodbank_id = tmp.foodbank_id;""", 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# QUERY : LOW INVENTORY
class LowInventory(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
            SELECT tmp.foodbank_id, foodbank_name, food_id,item, averageOrder, qty, excess
            FROM (
                SELECT foodbank_id, item, excessList.food_id, averageOrder, qty, excess
                FROM (
                    SELECT inventory.foodbank_id, food_id, averageOrder, qty, (qty - averageOrder) as excess from (
                        SELECT foodbank_id, foodID, (count(foodID)/3) as averageOrder from(
                            SELECT foodbank_id, trim('"' from cast(json_extract(list, val) as CHAR)) as foodID
                            from orders
                            join numbers on JSON_LENGTH(list) >= n
                            where DATE(STR_TO_DATE(timestamp, '%c-%e-%Y %H:%i:%s')) < '2021-07-04') temp
                        group by foodID, foodbank_id) ordercount
                    inner join inventory on foodID = food_id and ordercount.foodbank_id = inventory.foodbank_id
                    where qty < averageOrder)
                AS excessList
                LEFT JOIN food_list ON food_list.food_id = excessList.food_id)
            AS tmp
            LEFT JOIN foodbanks ON foodbanks.foodbank_id = tmp.foodbank_id;""", 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)


# QUERY : NO INVENTORY
class NoInventory(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
            SELECT food_list.food_id, item
            FROM food_list
            LEFT JOIN inventory ON food_list.food_id = inventory.food_id
            WHERE qty = 0 OR qty IS NULL;""", 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)


# CUSTOMER QUERIES - WINSTON

# Customer Order by Foodbank
class CustomerOrderValue(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
            SELECT user_id
                , first_name
                , last_name
                , t.foodbank_id
                , foodbank_name
                , round(sum(TotalQty*value),2) AS Total_Value
                FROM (
                    SELECT foodbank_id, user_id, foodID, count(foodID) AS TotalQty
                    FROM (
                        SELECT foodbank_id,
                        order_id,
                        user_id,
                        trim('"' FROM cast(json_extract(list, val) as CHAR)) AS foodID
                        FROM orders JOIN numbers ON JSON_LENGTH(list) >= n) AS temp
                        group by temp.user_id, foodID, foodbank_id) as  t
            JOIN food_list ON food_id = foodID
            JOIN foodbanks f ON t.foodbank_id = f.foodbank_id
            JOIN customer c ON t.user_id = c.customer_id
            GROUP BY t.user_id, t.foodbank_id; """, 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)
            
            
# FOODBANK QUERIES - PRASHANT

# Customer Order by Foodbank
class Foodbanks(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
            SELECT * FROM feed_the_hungry.foodbanks;""", 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)


# -- Queries end here -------------------------------------------------------------------------------

# Add Comment Here ie Shows All Meal Plan Info
class TemplateApi(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute(""" SELECT
                                *
                                FROM
                                ptyd_meal_plans;""", 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# Define API routes

# Still uses getRdsConn()
# Needs to be converted to V2 APIs
#api.add_resource(Meals, '/api/v1/meals')
#api.add_resource(Accounts, '/api/v1/accounts')

# New APIs, uses connect() and disconnect()
# Create new api template URL
# DONOR QUERIES - ROHAN
api.add_resource(TemplateApi, '/api/v2/templateapi')
api.add_resource(DonorValuation, '/api/v2/donordonation')
api.add_resource(ItemDonations, '/api/v2/itemdonations')
api.add_resource(TypesOfFood, '/api/v2/foodtypes')
api.add_resource(DonationbyDate, '/api/v2/donation')
# ORDER QUERIES - PRAGYA
api.add_resource(OrderStatus, '/api/v2/orderstatus')
# CUSTOMER QUERIES  - WINSTON
api.add_resource(CustomerOrderValue, '/api/v2/customervalue')
# INVENTORY QUERIES - ISSEI
api.add_resource(ExcessInventory, '/api/v2/excess')
api.add_resource(LowInventory, '/api/v2/low')
api.add_resource(NoInventory, '/api/v2/zero')
# FOODBANK QUERIES - PRASHANT
api.add_resource(Foodbanks, '/api/v2/foodbanks')


# Run on below IP address and port
# Make sure port number is unused (i.e. don't use numbers 0-1023)
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=4000)
